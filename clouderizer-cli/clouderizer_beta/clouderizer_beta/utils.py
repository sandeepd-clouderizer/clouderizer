# Copyright 2019 Atalaya Tech, Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import shutil
import logging
import re
import tarfile
from pathlib import Path
import json
import requests

# import boto3
# from botocore.exceptions import ClientError

# from bentoml.exceptions import BentoMLException
# from bentoml.yatai.deployment.aws_utils import call_sam_command
import subprocess
from clouderizer_beta import globals

logger = logging.getLogger(__name__)

# Maximum size for Lambda function bundle 250MB, leaving 1mb offset
LAMBDA_FUNCTION_LIMIT = 249000000
# Total disk size that user has access to.  Lambda function bundle + /tmp 512MB, leaving
# 1mb offset
LAMBDA_TEMPORARY_DIRECTORY_MAX_LIMIT = 511000000
LAMBDA_FUNCTION_MAX_LIMIT = LAMBDA_FUNCTION_LIMIT + LAMBDA_TEMPORARY_DIRECTORY_MAX_LIMIT

def get_command(project_dir):
	code, stdout, stderr = call_bash(["sudo","sam"],project_dir)

	# print(code)
	# print(stdout)
	# print(stderr)

	if "not found" in stderr or code != 0:
		return False
	return True

def call_sam_command(command, project_dir, region):

	if get_command(project_dir):
		command = ["sudo","sam"] + command
	else:
		command = ["sam"] + command

	# We are passing region as part of the param, due to sam cli is not currently
	# using the region that passed in each command.  Set the region param as
	# AWS_DEFAULT_REGION for the subprocess call
	logger.debug('Setting envar "AWS_DEFAULT_REGION" to %s for subprocess call', region)
	copied_env = os.environ.copy()
	copied_env["AWS_DEFAULT_REGION"] = region

	proc = subprocess.Popen(
		command,
		cwd=project_dir,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		env=copied_env,
	)
	stdout, stderr = proc.communicate()
	logger.debug("SAM cmd %s output: %s", command, stdout.decode("utf-8"))
	return proc.returncode, stdout.decode("utf-8"), stderr.decode("utf-8")

def call_bash(command, project_dir):
	proc = subprocess.Popen(
		command,
		cwd=project_dir,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
	)
	stdout, stderr = proc.communicate()
	# logger.debug("SAM cmd %s output: %s", command, stdout.decode("utf-8"))
	return proc.returncode, stdout.decode("utf-8"), stderr.decode("utf-8")


def prepend_line(file_path, line):
	""" Insert given string as a new line at the beginning of a file """
	# define name of temporary dummy file
	file_name=file_path.split("/")[-1]
	dummy_file = file_path + '.bak'
	# open original file in read mode and dummy file in write mode
	with open(file_path, 'r') as read_obj, open(dummy_file, 'w') as write_obj:
		# Write given line to the dummy file
		write_obj.write(line + '\n')
		# Read lines from original file one by one and append them to the dummy file
		for line in read_obj:
			write_obj.write(line)
	# remove original file
	os.remove(file_path)
	# Rename dummy file as the original file
	os.rename(dummy_file, file_path)

def parse_json(data):
	try:
		data=json.loads(data)
		return data
	except Exception as e:
		return "Some error occurred"

def upload_to_showcase(base_url,file_name,file_loc,company,auth_token):
	upload_endpoint = base_url + '/api/awsconfig/generatepresignedurl'
	# print("Uploading {} to Clouderizer.....".format(file_name))
	resp=requests.post(upload_endpoint,json={
			"type":"put",
			"key": file_name,
			"company": company
	},headers={"Content-Type":"application/json","Authorization": "Bearer "+auth_token})

	# print(resp.text)
	resp=parse_json(resp.text)
	# resp=json.loads(resp.text)

	if resp['success'] and "urls" in resp and len(resp["urls"])>0:
		print("Upload in progress.......")
		# print(resp)
		f=open(file_loc,'rb')

		aws_response=requests.put(resp['urls'][0],data=f)
		if(aws_response.status_code==200):
			print("Upload successful.")
			return "Success"
		else:
			return "Some error occurred while uploading... try again"
			# status_response=requests.post(status_endpoint,json={
			#     "filename": file_name,
			#     "secret_key": secret_key
			# },headers={"Content-Type":"application/json"})
	return "Some error occurred while uploading... try again"

def get_creds():
	globals.init()
	creds=None
	if os.path.exists(globals.LOCAL_PATH):
		with open(globals.LOCAL_PATH, 'r') as token:
			data=token.read()
			if os.stat(globals.LOCAL_PATH).st_size != 0:
				# try:
				creds = parse_json(data)
				# except Exception as e:
				#   print(e)
				#   print("Couldn't verify your credentials, please login again")
				#   return
				return creds
			else:
				print("You are not logged in, try: cldz login.")
				exit(0)
		return creds
	else:
		print("You are not logged in, try: cldz login")
		exit(0)

# def init_sam_project(
#     sam_project_path,
#     bento_service_bundle_path,
#     deployment_name,
#     bento_name,
#     api_names,
#     aws_region,
# ):
#     function_path = os.path.join(sam_project_path, deployment_name)
#     os.mkdir(function_path)
#     # Copy requirements.txt
#     logger.debug("Copying requirements.txt")
#     requirement_txt_path = os.path.join(bento_service_bundle_path, "requirements.txt")
#     shutil.copy(requirement_txt_path, function_path)

#     bundled_dep_path = os.path.join(
#         bento_service_bundle_path, "bundled_pip_dependencies"
#     )
#     if os.path.isdir(bundled_dep_path):
#         # Copy bundled pip dependencies
#         logger.debug("Copying bundled_dependencies")
#         shutil.copytree(
#             bundled_dep_path, os.path.join(function_path, "bundled_pip_dependencies")
#         )
#         bundled_files = os.listdir(
#             os.path.join(function_path, "bundled_pip_dependencies")
#         )
#         for index, bundled_file_name in enumerate(bundled_files):
#             bundled_files[index] = "./bundled_pip_dependencies/{}\n".format(
#                 bundled_file_name
#             )

#         logger.debug("Updating requirements.txt")
#         with open(
#             os.path.join(function_path, "requirements.txt"), "r+"
#         ) as requirement_file:
#             required_modules = bundled_files + requirement_file.readlines()
#             # Write from beginning of the file, instead of appending to the end.
#             requirement_file.seek(0)
#             requirement_file.writelines(required_modules)

#     # Copy bento_service_model
#     logger.debug("Copying model directory")
#     model_path = os.path.join(bento_service_bundle_path, bento_name)
#     shutil.copytree(model_path, os.path.join(function_path, bento_name))

#     logger.debug("Creating python files for lambda function")
#     # Create empty __init__.py
#     open(os.path.join(function_path, "__init__.py"), "w").close()

#     app_py_path = os.path.join(os.path.dirname(__file__), "lambda_app.py")
#     shutil.copy(app_py_path, os.path.join(function_path, "app.py"))
#     unzip_requirement_py_path = os.path.join(
#         os.path.dirname(__file__), "download_extra_resources.py"
#     )
#     shutil.copy(
#         unzip_requirement_py_path,
#         os.path.join(function_path, "download_extra_resources.py"),
#     )

#     logger.info("Building lambda project")
#     return_code, stdout, stderr = call_sam_command(
#         ["build", "--use-container", "--region", aws_region],
#         project_dir=sam_project_path,
#         region=aws_region,
#     )
#     if return_code != 0:
#         error_message = stderr
#         if not error_message:
#             error_message = stdout
#         raise BentoMLException(
#             "Failed to build lambda function. {}".format(error_message)
#         )
#     logger.debug("Removing unnecessary files to free up space")
#     for api_name in api_names:
#         cleanup_build_files(sam_project_path, api_name)


def cleanup_build_files(project_dir, api_name):
	build_dir = os.path.join(project_dir, ".aws-sam/build/{}".format(api_name))
	logger.debug("Cleaning up unused files in SAM built directory %s", build_dir)
	for root, dirs, files in os.walk(build_dir):
		if "tests" in dirs:
			logger.debug("removing dir: %s", os.path.join(root, "tests"))
			shutil.rmtree(os.path.join(root, "tests"))
		if "__pycache__" in dirs:
			logger.debug("removing dir: %s", os.path.join(root, "__pycache__"))
			shutil.rmtree(os.path.join(root, "__pycache__"))

		for dir_name in filter(lambda x: re.match("^.*\\.dist-info$", x), dirs):
			logger.debug("removing dir: %s", dir_name)
			shutil.rmtree(os.path.join(root, dir_name))

		for file in filter(lambda x: re.match("^.*\\.egg-info$", x), files):
			logger.debug("removing file: %s", os.path.join(root, file))
			os.remove(os.path.join(root, file))

		for file in filter(lambda x: re.match("^.*\\.pyc$", x), files):
			logger.debug("removing file: %s", os.path.join(root, file))
			os.remove(os.path.join(root, file))

		if "wheel" in files:
			logger.debug("removing file: %s", os.path.join(root, "wheel"))
			os.remove(os.path.join(root, "wheel"))
		if "pip" in files:
			logger.debug("removing file: %s", os.path.join(root, "pip"))
			os.remove(os.path.join(root, "pip"))
		if "caff2" in files:
			logger.debug("removing file: %s", os.path.join(root, "caff2"))
			os.remove(os.path.join(root, "caff2"))


# def lambda_package(project_dir, aws_region, s3_bucket_name, deployment_prefix):
#     prefix_path = os.path.join(deployment_prefix, "lambda-functions")
#     build_dir = os.path.join(project_dir, ".aws-sam", "build")

#     return_code, stdout, stderr = call_sam_command(
#         [
#             "package",
#             "--force-upload",
#             "--s3-bucket",
#             s3_bucket_name,
#             "--s3-prefix",
#             prefix_path,
#             "--template-file",
#             "template.yaml",
#             "--output-template-file",
#             "packaged.yaml",
#             "--region",
#             aws_region,
#         ],
#         project_dir=build_dir,
#         region=aws_region,
#     )
#     if return_code != 0:
#         error_message = stderr
#         if not error_message:
#             error_message = stdout
#         raise BentoMLException(
#             "Failed to package lambda function. {}".format(error_message)
#         )
#     else:
#         return stdout


def lambda_deploy(project_dir, aws_region, stack_name):
	# if the stack name exists and the state is in rollback_complete or
	# other 'bad' state, we will delete the stack first, and then deploy
	# it
	logger.debug('Ensure stack "%s" is ready to deploy', stack_name)
	ensure_is_ready_to_deploy_to_cloud_formation(stack_name, aws_region)
	logger.debug('Stack "%s"is ready to deploy', stack_name)

	template_file = os.path.join(project_dir, ".aws-sam", "build", "packaged.yaml")
	return_code, stdout, stderr = call_sam_command(
		[
			"deploy",
			"--stack-name",
			stack_name,
			"--capabilities",
			"CAPABILITY_IAM",
			"--template-file",
			template_file,
			"--region",
			aws_region,
		],
		project_dir=project_dir,
		region=aws_region,
	)
	if return_code != 0:
		error_message = stderr
		if not error_message:
			error_message = stdout
		raise BentoMLException(
			"Failed to deploy lambda function. {}".format(error_message)
		)
	else:
		return stdout


# def total_file_or_directory_size(file_or_dir):
#     if os.path.isdir(file_or_dir):
#         return sum(
#             f.stat().st_size for f in Path(file_or_dir).glob("**/*") if f.is_file()
#         )
#     else:
#         return Path(file_or_dir).stat().st_size


def check_aws_cli_exists():
	return_code, stdout, stderr = call_bash(["aws"],os.getcwd())

	# print(return_code)
	# print(stdout)
	# print(stderr)

	if "not found" in stdout or "not found" in stderr:
		print("Lambda deployment needs aws cli to be installed : https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html")
		exit(0)

	# return_code, stdout, stderr = call_bash["aws","sts","get-caller-identity"]

	# if "Unable to locate credentials" in stdout or "Unable to locate credentials" in stderr:
	#     print("aws not configured : aws configure")
	#     exit(0)

def check_sam_cli_exists():
	eturn_code, stdout, stderr = call_bash(["sam"],os.getcwd())

	# print(return_code)
	# print(stdout)
	# print(stderr)

	if "not found" in stdout or "not found" in stderr:
		print("Lambda deployment needs sam cli to be installed : https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html")
		exit(0)

# def reduce_bundle_size_and_upload_extra_resources_to_s3(
#     build_directory,
#     region,
#     s3_bucket,
#     deployment_prefix,
#     function_name,
#     lambda_project_dir,
# ):
#     additional_requirements_path = os.path.join(
#         lambda_project_dir, "additional_requirements", function_name
#     )
#     upload_dir_path = os.path.join(additional_requirements_path, "requirements")
#     os.makedirs(upload_dir_path, exist_ok=True)
#     s3_client = boto3.client("s3", region)

#     dir_name_to_size = dict(
#         (item, total_file_or_directory_size(os.path.join(build_directory, item)))
#         for item in os.listdir(build_directory)
#     )

#     required_bundle_list = ["app.py", "__init__.py", "download_extra_resources.py"]
#     required_bundle_size = sum(dir_name_to_size[i] for i in required_bundle_list)
#     for name, size in sorted(
#         dir_name_to_size.items(), key=lambda i: i[1], reverse=True
#     ):
#         if name in required_bundle_list:
#             logger.debug('Including "%s" it is part of required bundle.', name)
#             continue
#         else:
#             new_bundle_size = required_bundle_size + size
#             if new_bundle_size >= LAMBDA_FUNCTION_LIMIT:
#                 logger.debug(
#                     'Lambda function size %d is over the limit. Moving item "%s" '
#                     "out of the bundle directory",
#                     new_bundle_size,
#                     name,
#                 )
#                 package_path = os.path.join(build_directory, name)
#                 copy_dst_path = os.path.join(upload_dir_path, name)
#                 shutil.move(package_path, copy_dst_path)
#             else:
#                 logger.debug(
#                     'Including "%s" Now the current lambda function size is %d',
#                     name,
#                     new_bundle_size,
#                 )
#                 required_bundle_size = new_bundle_size

#     logger.debug("Final Lambda function bundle size is %d", required_bundle_size)
#     additional_requirements_size = total_file_or_directory_size(
#         additional_requirements_path
#     )
#     logger.debug("Additional requirement size is %d", additional_requirements_size)
#     logger.debug("zip up additional requirement packages")
#     tar_file_path = os.path.join(additional_requirements_path, "requirements.tar")
#     with tarfile.open(tar_file_path, "w:gz") as tar:
#         tar.add(upload_dir_path, arcname="requirements")
#     logger.debug("Uploading requirements.tar to %s/%s", s3_bucket, deployment_prefix)
#     try:
#         s3_client.upload_file(
#             tar_file_path,
#             s3_bucket,
#             os.path.join(deployment_prefix, "requirements.tar"),
#         )
#     except ClientError as e:
#         raise BentoMLException(str(e))


# def ensure_is_ready_to_deploy_to_cloud_formation(stack_name, region):
#     try:
#         cf_client = boto3.client("cloudformation", region)
#         logger.debug("Checking stack description")
#         describe_formation_result = cf_client.describe_stacks(StackName=stack_name)
#         result_stacks = describe_formation_result.get("Stacks")
#         if len(result_stacks):
#             logger.debug('Stack "%s" exists', stack_name)
#             stack_result = result_stacks[0]
#             if stack_result["StackStatus"] in [
#                 "ROLLBACK_COMPLETE",
#                 "ROLLBACK_FAILED",
#                 "ROLLBACK_IN_PROGRESS",
#             ]:
#                 logger.debug(
#                     'Stack "%s" is in a "bad" status(%s), deleting the stack '
#                     "before deployment",
#                     stack_name,
#                     stack_result["StackStatus"],
#                 )
#                 cf_client.delete_stack(StackName=stack_name)
#     except ClientError as e:
#         # We are brutally parse and handle stack doesn't exist, since
#         # "AmazonCloudFormationException" currently is not implemented in boto3. Once
#         # the current error is implemented, we need to switch
#         error_response = e.response.get("Error", {})
#         error_code = error_response.get("Code")
#         error_message = error_response.get("Message", "Unknown")
#         if error_code == "ValidationError" and "does not exist" in error_message:
#             pass
#         else:
#             raise BentoMLException(str(e))
