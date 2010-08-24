#!/usr/bin/env python
import optparse
import sys
import string
from subprocess import call
from mercurial import hg, ui
from mercurial.error import RepoError

class Dumper(object):
    """
    Main class that defines how to store database dumps in version control.
    Will be subclassed for the different database backends to handle the
    different methods of doing the actual dump.
    """

    def __init__(self, backend, options):
        self.backend = backend
        self.database = options.database
        self.username = options.username
        self.password = options.password
        self.mirror = options.mirror
        
        if options.repository is not None:
            self.path = options.repository
        else:
            self.path = 'adamanteus_%s_%s_backup' % (self.database, self.backend)
        print 'Preparing to back up a %s database to repository %s' % (self.backend, self.path)

        try:
            self.repo = hg.repository(ui.ui(), path=self.path)
        except RepoError:
            self.repo = hg.repository(ui.ui(), path=self.path, create=True)

    def __call__(self):
        self.dump()
        self.store()
        if self.mirror is not None:
            self.push()

    def dump(self):
        raise NotImplementedError("You must subclass Dumper and define "
                                  "your own dump() method.")

    def store(self):
        status = self.repo.status(unknown=True)
        unknown = status[4]
        len_unknown = len(unknown)
        missing = status[3]
        len_missing = len(missing)
        workingctx = self.repo[None]
        
        if len_unknown:
            print "Adding %d files to repo..." % len_unknown
            workingctx.add(unknown)
        if len_missing:
            print "Removing %d missing files from repo..." % len_unknown
            workingctx.remove(missing)
        if len(self.repo.status()[0]) or len(self.repo.status()[1]):
            rev = self.repo.commit()

    def push(self):
        remote_paths = self.mirror.split(',')
        for remote_path in remote_paths:
            remote_repo = hg.repository(ui.ui(), path=remote_path)
            self.repo.push(remote_repo)

class MongoDumper(Dumper):
    """
    Subclass of Dumper for working with MongoDB databases.
    """

    def dump(self):
        try:
            from pymongo.connection import Connection
            connection = Connection()
            collections = connection[self.database].collection_names()
            for collection in collections:
                dump_options = ['mongoexport', '-d%s' % self.database, '-c%s' % collection]
                if self.username is not None:
                    dump_options.append('-u %s' % self.username)
                if self.password is not None:
                    dump_options.append('-p %s' % self.password)
                output_file = "%s/%s.json" % (self.path, collection)
                dump_options.append('-o%s' % output_file)
                call(dump_options)
        except ImportError:
            # For now we need to use mongodump, will switch to
            # mongoexport with MongoDB 1.5
            dump_options = ['mongodump', '--out=%s' % self.path, '-d%s' % self.database]
            if self.username is not None:
                dump_options.append('-u %s' % self.username)
            if self.password is not None:
                dump_options.append('-p %s' % self.password)
            call(dump_options)

class MySQLDumper(Dumper):
    """
    Subclass of Dumper for working with MySQL databases.
    """

    def dump(self):
        # mysqldump -u 'username' -ppassword --skip-extended-insert database > $FILENAME
        output_file = "%s/%s.sql" % (self.path, self.database)
        
        dump_options = ['mysqldump']
        if self.username is not None:
            dump_options.append("-u%s" % string.strip(self.username))
        if self.password is not None:
            dump_options.append('-p%s' % self.password)
        dump_options.append('--skip-extended-insert')
        dump_options.append(self.database)
        dump_options.append('--result-file=%s' % output_file)
        call(dump_options)

class PostgresDumper(Dumper):
    """
    Sublcass of Dumper for working with PostgreSQL databases.
    """

    def dump(self):
        # pg_dump django_influencer -U username -W --file=filename

        # There's apparently no way to pass in a password at the command line,
        # so looks like we'll just have to leave that out. Will return an error
        # if the user tries to give a password for a PostgreSQL database dump.
        if self.password is not None:
            password_error = """
PostgreSQL dumper does not support password authentication.
Please set up a read-only user for backing up your PostgreSQL database, or use a .pgpass file.
Details on using a .pgpass file can be found here: http://www.postgresql.org/docs/current/interactive/libpq-pgpass.html
"""
            raise Exception(password_error)
        output_file = "%s/%s.out" % (self.path, self.database)

        dump_options = ['pg_dump', self.database]
        # options get set here
        if self.username is not None:
            dump_options.append('-U%s' % string.strip(self.username))

        dump_options.append('--file=%s' % output_file)
        call(dump_options)
            
def main():
    usage = "usage: %prog BACKEND -d DATABASE [-r repository] [-u username] [-p password]"
    p = optparse.OptionParser(description=' Backup a database to a mercurial repository',
                              prog='adamanteus',
                              version='adamanteus 0.6',
                              usage=usage)
    p.add_option('--database', '-d', default=None,
                 help="The name of the database to be backed up.")
    p.add_option('--repository', '-r', default=None,
                 help="The mercurial repository to be backed up to.")
    p.add_option('-u', default=None, dest='username',
                 help="The username to use with the database.")
    p.add_option('--password', '-p', default=None,
                 help="The password to use with the database.")
    p.add_option('--mirror', '-m', default=None,
                 help="Remote repository to be used as mirror of backup.")
    options, arguments = p.parse_args()

    DUMPERS = {
        'mongodb': MongoDumper,
        'mysql': MySQLDumper,
        'postgres': PostgresDumper,
        }

    if len(arguments) != 1:
        p.print_usage()
        print >> sys.stderr, 'You must specify a database backend.'
        return
    else:
        backend = arguments[0]
    if backend not in DUMPERS.keys():
        print >> sys.stderr, '%s is not currently a supported database backend.' % backend
        print >> sys.stderr, 'Supported backends include: %s.' % ', '.join(DUMPERS.keys())
        return
    if options.database is None:
        print p.print_usage()
        print >> sys.stderr, 'You must specify a database to be backed up.'
        return

    dumper = DUMPERS[backend](backend, options)
    dumper()
    
if __name__ == '__main__':
    main()

