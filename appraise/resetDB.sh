#!/bin/bash

export ESMT_CAMPAIGN=testing

python2 manage.py reset corpus --noinput
python2 manage.py reset evaluation --noinput
python2 manage.py syncdb
./esmt add language -i ES -l Spanish -n Español
./esmt add language -i DE -l German -n Deutsch
#./esmt add campaign testing
./esmt add document test/source-ES -l ES -u
./esmt add document test/source-ES-2 -l ES -u
./esmt add document test/source-DE -l DE -u
./esmt add corpus -i corpus1 -l ES source-ES source-ES-2
./esmt add system jane
./esmt add system moses
./esmt add system lucy
./esmt add translation -i source-ES -s jane test/transJane-DE -l DE
./esmt add translation -i source-ES -s moses test/transMoses-DE -l DE
./esmt add translation -i source-ES -s lucy test/transLucy-DE -l DE
