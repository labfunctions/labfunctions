import logging
import os
import pathlib
import subprocess
from typing import Optional, Union
from zipfile import ZipFile

from nb_workflows import secrets
from nb_workflows.conf import defaults

from .types import Credentials, ProjectZipFile

logger = logging.getLogger(__name__)


def execute(cmd) -> str:
    with subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as p:

        out, err = p.communicate()
        if err:
            raise AttributeError(err.decode())

        return out.decode().strip()


def write_secrets(root, private_key, vars_file) -> str:
    _vars = secrets.encrypt_nbvars(private_key, vars_file)
    newline = "\n"
    encoded_vars = f'{newline.join(f"{key}={value}" for key, value in _vars.items())}'
    outfile = root / defaults.CLIENT_TMP_FOLDER / defaults.SECRETS_FILENAME
    with open(outfile, "w") as f:
        f.write(encoded_vars)

    return outfile


def short_head_id():
    return execute("git rev-parse --short HEAD")


def zip_git_current(
    root, prefix_folder=defaults.ZIP_GIT_PREFIX
) -> Union[ProjectZipFile, None]:
    """Zip the actual folder state
    using git stash, this should be used only when testing or developing
    """
    # project = str(root).rsplit("/", maxsplit=1)[-1]

    secrets_file = root / defaults.CLIENT_TMP_FOLDER / defaults.SECRETS_FILENAME

    output_file = f"{str(root)}/{defaults.CLIENT_TMP_FOLDER}/CURRENT.zip"
    stash_id = execute("git stash create")
    if not stash_id:
        return None
    cmd = (
        f"git archive --prefix={prefix_folder} "
        f"--add-file {secrets_file} "
        f"-o {output_file} {stash_id} "
    )

    execute(cmd)

    return ProjectZipFile(filepath=output_file, current=True)


def zip_git_head(root) -> ProjectZipFile:
    """Zip the head of the repository.
    Not commited files wouldn't included in this zip file
    """
    # project = str(root).rsplit("/", maxsplit=1)[-1]
    id_ = short_head_id()
    output_file = f"{str(root)}/{defaults.CLIENT_TMP_FOLDER}/HEAD-{id_}.zip"
    execute(f"git archive -o {output_file} HEAD")
    return ProjectZipFile(filepath=output_file, commit=id_)


def zip_project(root, secrets_file, current=False) -> ProjectZipFile:
    """Make a zip of this project.
    It uses git to skip files in the .gitignore file.
    After making the zip file with git,  it will add a secret file
    with the values of "[filename].nbvars" encrypted on it.

    :param dev: default False, if True it will make a git stash
    of the current files. If False, then will zip the last commited changes.
    """

    # secrets_file = write_secrets(root, private_key, vars_file)

    zfile = None

    if current:
        zfile = zip_git_current(root)
        if not zfile:
            raise TypeError(
                "There isn't changes in the git repository to perform a CURRENT zip file. For untracked files you should add to the stash the changes, perform: git add ."
            )

    return zfile


def manage_upload(privkey, env_file, current, creds: Credentials) -> ProjectZipFile:
    """
    it manages how to upload project files to the server.
    """

    secrets.nbvars["AGENT_TOKEN"] = creds.access_token
    secrets.nbvars["AGENT_REFRESH_TOKEN"] = creds.refresh_token

    root = pathlib.Path(os.getcwd())
    (root / defaults.CLIENT_TMP_FOLDER).mkdir(parents=True, exist_ok=True)

    secrets_file = write_secrets(root, privkey, env_file)
    zfile = zip_project(root, secrets_file, current)

    pathlib.Path(secrets_file).unlink(missing_ok=True)

    return zfile