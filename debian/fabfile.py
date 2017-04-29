#!/usr/bin/env python
from __future__ import print_function

# FIXME trusty needs an additional https://launchpad.net/~nschloe/+archive/ubuntu/cmake-backports
# FIXME trusty needs an additional deb http://archive.ubuntu.com/ubuntu trusty-backports universe for swig3

import abc
import atexit
import re
import os
import tempfile
from datetime import datetime
from textwrap import dedent

from fabric.api import abort, lcd, local
from fabric.colors import red

RESULT_DIR_BASE = "result/{dist}"
LOG_DIR = "log"

FIFE_DEBIAN_FILES_DIR = "fife_debian_files"
FIFE_GIT_DIR = "fifengine"

FIFECHAN_DEBIAN_FILES_DIR = "fifechan_debian_files"
FIFECHAN_GIT_DIR = "fifechan"

CHROOT_DEFAULT_BASE_PATH = os.environ.get('CHROOT_DEFAULT_BASE_PATH', 'chroots')
CHROOT_DEFAULT_MIRROR = 'http://httpredir.debian.org/debian'
CHROOT_UBUNTU_MIRROR = 'http://ubuntu.mirror.tudos.de/ubuntu/'

os.environ['DEBEMAIL'] = 'debian@unknown-horizons.org'
os.environ['DEBFULLNAME'] = 'Unknown Horizons Autopackager'

GPG_KEY = 'debian@unknown-horizons.org'
GPG_PASSPHRASE_FILE = '../gpg.passphrase'


def _dist_supported(dist, debian_files_dir):
	"""Checks if the given distribution is supported."""
	if dist == "master":
		abort('"master" is no distribution.')
	local('cd {}'.format(debian_files_dir))
	with lcd(debian_files_dir):
		branches = local('git branch', capture=True)
	searched_regex = '^(?:[ *] )?{}$'.format(dist)
	return re.search(searched_regex, branches, re.MULTILINE) is not None


def show_env():
	local('env')


def list_dists():
	"""List all supported dists."""
	with lcd(FIFE_DEBIAN_FILES_DIR):
		local('git branch | grep -v " master$" | cut -d " " -f 2-')


def create_build_chroot(dist, mirror=CHROOT_DEFAULT_MIRROR, base_path=CHROOT_DEFAULT_BASE_PATH, components='main', pbuilder_opts=''):
	"""Create a cowbuilder chroot to be used for building."""
	path = os.path.join(base_path, '{}.cow'.format(dist))
	if os.path.exists(path):
		abort('The path "{}" already exists.'.format(path))
	local('sudo cowbuilder --create --basepath {} --distribution {} --mirror {} --components "{}" {}'.format(path, dist, mirror, components, pbuilder_opts))


def create_ubuntu_build_chroot(dist, base_path=CHROOT_DEFAULT_BASE_PATH):
	# jessie debootstrap does not take ubuntu-archive-keyring into account. We
	# need to tell it to do that explicitly.
	return create_build_chroot(dist, CHROOT_UBUNTU_MIRROR, base_path, 'main universe', pbuilder_opts='--debootstrapopts "--keyring=/usr/share/keyrings/ubuntu-archive-keyring.gpg"')


def update_build_chroot(dist, base_path=CHROOT_DEFAULT_BASE_PATH):
	"""Update a cowbuilder chroot."""
	path = os.path.join(base_path, '{}.cow'.format(dist))
	local('sudo cowbuilder --update --basepath {}'.format(path))


class Builder(object):
	__metaclass__ = abc.ABCMeta

	debian_files_dir = None
	git_dir = None
	project_name = None
	github_repo = None

	def build(self, commit, dist, **kwargs):
		build_start = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')

		if not _dist_supported(dist, self.debian_files_dir):
			abort('The given distribution is not supported.')

		self.basepath = os.path.join(os.path.abspath(CHROOT_DEFAULT_BASE_PATH), '{}.cow'.format(dist))
		if not os.path.exists(self.basepath):
			# TODO: just create it ... needs a list of ubuntu/debian dist names
			abort('The corresponding build dir does not exist. Please create one, first.')

		if not os.path.exists(self.git_dir):
			local('git clone {} {}'.format(self.github_repo, self.git_dir))

		if not os.path.exists(LOG_DIR):
			os.mkdir(LOG_DIR)
		
		self.result_dir = os.path.abspath(RESULT_DIR_BASE.format(dist=dist))
		if not os.path.exists(self.result_dir):
			os.makedirs(self.result_dir)

		with lcd(self.git_dir):
			local('git remote update')
			# TODO maybe use git workdir here, so we can build in parallel
			# also checks if the given commit exists
			local('git checkout {}'.format(commit))

			version = self._get_version()

			commit_date = local("git show --format='format:%ci' | head -n 1 | cut -d ' ' -f 1 | tr -d '-'", capture=True)
			commit_hash = local("git show --format='format:%h' | head -n 1", capture=True)
			version_append = '+git{}-{}'.format(commit_date, commit_hash)
	
		# create a temporary build dir
		tmp_dir = tempfile.mkdtemp()
		def _remove_tmp_dir_on_exit():
			local('rm -rf {}'.format(tmp_dir))
		atexit.register(_remove_tmp_dir_on_exit)
		with lcd(tmp_dir):
			# TODO variable?!
			self.build_dir = os.path.join(tmp_dir, self.project_name)
			os.mkdir(self.build_dir)
			self.hook_dir = os.path.join(tmp_dir, 'hooks')
			os.mkdir(self.hook_dir)
		#print(red(tmp_dir))
		
		# get a tarball of the commit
		with lcd(self.git_dir):
			tar_name = '{}_{}{}.orig.tar'.format(self.project_name, version, version_append)
			tar_path = os.path.join(tmp_dir, tar_name)
			local('git archive -o "{}" HEAD'.format(tar_path))
		
		# bzip the tarball
		local('bzip2 -f "{}"'.format(tar_path))
		tar_path = '{}.bz2'.format(tar_path)

		# get a tarball of the debian files
		with lcd(self.debian_files_dir):
			debian_tar_path = os.path.join(tmp_dir, 'debian.tar')
			local('git checkout {}'.format(dist))
			local('git archive -o "{}" HEAD'.format(debian_tar_path))

		# unpack the tarballs
		with lcd(self.build_dir):
			local('tar -xjf "{}"'.format(tar_path))
			local('mkdir debian')
			local('tar -xf "{}" -C debian'.format(debian_tar_path))

		with lcd(self.build_dir):
			# change the version
			local('dch --distribution {} --newversion {}{}-1+{}1 --force-distribution "* build of a git version"'
				  .format(dist, version, version_append, dist))

		log_file = os.path.join(os.path.abspath(LOG_DIR), '{}_{}.log'.format(self.project_name, build_start))
		status_file = os.path.join(tmp_dir, 'pdebuild.status')

		self._final_build_steps(log_file, status_file, kwargs)

		#print(red('rm -rf {}'.format(tmp_dir)))
		return (version, version_append)
	
	@abc.abstractmethod
	def _get_version(self):
		pass
	
	@abc.abstractmethod
	def _final_build_steps(self, log_file, status_file, kwargs):
		pass


class FifeBuilder(Builder):
	debian_files_dir = FIFE_DEBIAN_FILES_DIR
	git_dir = FIFE_GIT_DIR
	project_name = "fife"
	github_repo = "https://github.com/fifengine/fifengine.git"

	def _get_version(self):
		versions = local("grep -E '^set *\(FIFE_(MAJOR|MINOR|PATCH)_VERSION' CMakeLists.txt", capture=True).splitlines()
		version = '.'.join(re.search('(\d+)', v).group(0) for v in versions)
		return version

	def _final_build_steps(self, log_file, status_file, kwargs):
		# determine necessary bindmounts needed for the hook
		bindmounts = self.result_dir

		# fill the hook dir with something that uses the build-result-stuff
		hook_file = os.path.join(self.hook_dir, 'D50deps') 
		with open(hook_file, 'w') as f:
			f.write(dedent("""\
				#!/bin/sh
				cd "{result_dir}"
				dpkg-scanpackages --multiversion . /dev/null > Packages
				echo "deb [trusted=yes] file://{result_dir} ./" >> /etc/apt/sources.list
				apt-get update
				""").format(result_dir=self.result_dir))
		local('chmod a+x {}'.format(hook_file))

		with lcd(self.build_dir):
			# FIXME set the fifechan version in the control file. use
			# kwargs['fifechan_version'] for this
			pass
	
		with lcd(self.build_dir):
			# build the package
			local('{{ pdebuild --buildresult {} -- --basepath {} --bindmounts {} --hookdir {}; echo $? > {}; }} | tee {}'
				  .format(self.result_dir, self.basepath, bindmounts, self.hook_dir, status_file, log_file))
			with open(status_file) as f:
				status = int(f.read())
			if status != 0:
				abort('pdebuild exited with non-zero status: {}'.format(status))


def build_fife(commit, dist, fifechan_version):
	return FifeBuilder().build(commit, dist, fifechan_version=fifechan_version)


class FifechanBuilder(Builder):
	debian_files_dir = FIFECHAN_DEBIAN_FILES_DIR
	git_dir = FIFECHAN_GIT_DIR
	project_name = "fifechan"
	github_repo = "https://github.com/fifengine/fifechan.git"
	
	def _get_version(self):
		versions = local("grep -E '^SET\((MAJOR|MINOR|PATCH)_VERSION' CMakeLists.txt", capture=True).splitlines()
		version = '.'.join(re.search('(\d+)', v).group(0) for v in versions)
		return version
	
	def _final_build_steps(self, log_file, status_file, kwargs):
		with lcd(self.build_dir):
			# build the package
			local('{{ pdebuild --buildresult {} -- --basepath {}; echo $? > {}; }} | tee {}'
				  .format(self.result_dir, self.basepath, status_file, log_file))
			with open(status_file) as f:
				status = int(f.read())
			if status != 0:
				abort('pdebuild exited with non-zero status: {}'.format(status))


def build_fifechan(commit, dist):
	return FifechanBuilder().build(commit, dist)


def build(fife_commit, fifechan_commit, dist):
	(version, version_append) = build_fifechan(fifechan_commit, dist)
	build_fife(fife_commit, dist, (version, version_append))


# FIXME rebuilding older versions does not work (because of finding newer
# fifechan stuff? could be fixed by setting the fifechan-version as dependency)

def publish(dist):
	"""Publishes all packages found in the result dir for the given dist."""
	repos = local('aptly repo list | grep -oE "\[[a-z]+\]" || true', capture=True).splitlines()
	if not '[{}]'.format(dist) in repos:
		local('aptly repo create -distribution={} {}'.format(dist, dist))
	
	result_dir = os.path.abspath(RESULT_DIR_BASE.format(dist=dist))
	if not os.path.exists(result_dir):
		# nothing to be done for that dist
		return

	local('aptly repo add -remove-files=true {} {}'.format(dist, result_dir))
	local('aptly publish repo -gpg-key={} -passphrase-file={} {}'
			.format(GPG_KEY, os.path.abspath(GPG_PASSPHRASE_FILE), dist))
