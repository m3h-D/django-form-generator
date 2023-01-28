from setuptools import setup
import subprocess

remote_version = (
    subprocess.run(["git", "describe", "--tags"], stdout=subprocess.PIPE)
    .stdout.decode("utf-8")
    .strip()
)

if "-" in remote_version:
    v,i,s = remote_version.split("-")
    remote_version = v + "+" + i + ".git." + s


setup(
    version=remote_version
)