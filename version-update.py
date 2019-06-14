#!/usr/bin/env python3
import os
import re
import sys
import semver
import subprocess
import gitlab

def git(*args):
    return subprocess.check_output(["git"] + list(args))

def verify_env_var_presence(name):
    if name not in os.environ:
        raise Exception(f"Expected the following environment variable to be set: {name}")

def extract_gitlab_url_from_project_url():
    project_url = os.environ['CI_PROJECT_URL']
    project_path = os.environ['CI_PROJECT_PATH']

    return project_url.split(f"/{project_path}", 1)[0]

def extract_merge_request_id_from_commit():
    message = git("log", "-1", "--pretty=%B")
    matches = re.search(r'(\S*\/\S*!)(\d+)', message.decode("utf-8"), re.M|re.I)
    
    if matches == None:
        return None

    return matches.group(2)

def retrieve_labels_from_merge_request(merge_request_id):
    if merge_request_id is None:
        return []
       
    project_id = os.environ['CI_PROJECT_ID']
    gitlab_private_token = os.environ['NPA_PASSWORD']

    gl = gitlab.Gitlab(extract_gitlab_url_from_project_url(), private_token=gitlab_private_token)
    gl.auth()

    project = gl.projects.get(project_id)
    merge_request = project.mergerequests.get(merge_request_id)

    return merge_request.labels

def bump(latest):
    merge_request_id = extract_merge_request_id_from_commit()
    labels = retrieve_labels_from_merge_request(merge_request_id)
    new_version = None
    print('MR Labels', labels)
    if "bump-major" in labels:
        print('Bump major')
        new_version = semver.bump_major(latest)
    elif "bump-minor" in labels:
        print('Bump minor')
        new_version = semver.bump_minor(latest)
    elif "bump-patch" in labels:
        print('Bump patch')
        new_version = semver.bump_patch(latest)
    elif "finalize-rc" in labels:
        print('Finalize rc')
        new_version = semver.finalize_version(latest)
    elif "bump-build":
        print('Bump build')
        new_version = semver.bump_build(new_version if new_version else latest)

    if "bump-rc" in labels and not "finalize-rc" in labels:
        print('Bump rc')
        new_version = semver.bump_prerelease(new_version if new_version else latest)
        new_version = semver.bump_build(new_version)

    return new_version if new_version else latest

def tag_repo(tag):
    repository_url = os.environ["CI_REPOSITORY_URL"]
    username = os.environ["NPA_USERNAME"]
    password = os.environ["NPA_PASSWORD"]

    push_url = re.sub(r'([a-z]+://)[^@]*(@.*)', rf'\g<1>{username}:{password}\g<2>', repository_url)

    git("remote", "set-url", "--push", "origin", push_url)
    git("tag", tag)
    git("push", "origin", tag)        

def main():
    env_list = ["CI_REPOSITORY_URL", "CI_PROJECT_ID", "CI_PROJECT_URL", "CI_PROJECT_PATH", "NPA_USERNAME", "NPA_PASSWORD"]
    [verify_env_var_presence(e) for e in env_list]
    latest = None
    try:
        latest = git("describe", "--abbrev=0", "--tags").decode().strip()
    except subprocess.CalledProcessError:
        # Default to version 1.0.0 if no tags are available
        version = "1.0.0"
    else:
        # Skip already tagged commits
        if '-' not in latest:
            print('Skip already tagged commits', latest)
            return 0

        version = bump(latest)

    print('Current version', latest)
    tag_repo(version)
    print('New version', version)

    return 0


if __name__ == "__main__":
    sys.exit(main())
