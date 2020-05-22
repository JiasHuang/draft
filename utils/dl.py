#!/usr/bin/env python

import os
import sys
import ftplib
import optparse
import ConfigParser

def readConfig(section, opts):
    local = os.path.expanduser('~')+'/.myconfig'
    if not os.path.exists(local):
        sys.exit()
    config = ConfigParser.ConfigParser()
    config.read(local)
    if not config.has_section(section):
        sys.exit()
    conf = {}
    for opt in opts:
        if config.has_option(section, opt):
            conf[opt] = config.get(section, opt)
        else:
            conf[opt] = None
    return conf

def get(section, source, target=None):
    target = target or os.path.basename(source)
    conf = readConfig(section, ['protocol', 'serverip', 'username', 'password', 'remotedir'])
    if conf['protocol'] == 'ftp':
        ftp = ftplib.FTP(conf['serverip'])
        ftp.login(conf['username'], conf['password'])
        if conf['remotedir']:
            ftp.cwd(conf['remotedir'])
        ftp.retrbinary('RETR %s' %(source), open(target, 'wb').write)
        ftp.quit()
        print('[download] %s/%s -> %s' %(conf['remotedir'] or '', source, target))
    if conf['protocol'] == 'sftp':
        cmd = 'echo get %s %s | sshpass -p %s sftp %s@%s:%s' %(
            source, target,
            conf['password'], conf['username'], conf['serverip'], conf['remotedir'] or '/')
        os.system(cmd)
    if conf['protocol'] == 'smb':
        cmd = 'echo %s | smbclient -U %s %s -D %s -c \'get %s %s\'' %(
            conf['password'], conf['username'], conf['serverip'], conf['remotedir'],
            source, target)
        os.system(cmd)
    return

def download(section, source, target=None):
    if not target:
        target = os.path.basename(source)
    get(section, source, target)
    return

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option("-S", dest="section")
    parser.add_option("-s", dest="source")
    parser.add_option("-i", dest="source")
    parser.add_option("-t", dest="target")
    parser.add_option("-o", dest="target")
    options, args = parser.parse_args()

    if not options.source and len(args) >= 1:
        options.source = args[0].strip()

    if not options.target and len(args) >= 2:
        options.target = args[1].strip()

    if options.source:
        download(options.section or 'ftp', options.source, options.target)
