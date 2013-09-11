#!/bin/bash


python2 manage.py flush
python2 manage.py syncdb
./esmt add language -i ES -l Spanish -n Español
./esmt add language -i DE -l German -n Deutsch
./esmt add document test/source-ES -l ES --idfile test/source.ids
./esmt add document test/source-DE -l DE --idfile test/source.ids
./esmt add corpus -i corpus1 -l ES source-ES source-ES-2 
./esmt add system jane
./esmt add system moses
./esmt add system lucy
./esmt add translation -i corpus1 -s jane test/translation-corpus1-jane -l DE
./esmt add translation -i corpus1 -s moses test/translation-corpus1-moses -l DE
./esmt add translation -i corpus1 -s lucy test/translation-corpus1-lucy -l DE
./esmt add task -t ranking -c corpus1 -s jane,moses,lucy -n fromCmdLine -u wizard -l DE -R
./esmt add task -n post-edit-all -t post-edit-all -s jane,moses -l DE -c corpus1 -u wizard
./esmt add task -n select-and-post-edit -t select-and-post-edit -s jane,moses,lucy -l DE -c corpus1 -u wizard
./esmt add errorType MissingWord
./esmt add errorType Terminology
./esmt add errorType LexicalChoice
./esmt add errorType Syntax
./esmt add task -n error-classification -t error-classification -s jane,moses,lucy -l DE -c corpus1 -u wizard -e MissingWord,Terminology,LexicalChoice,Syntax
