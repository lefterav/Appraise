#!/bin/bash
python2 manage.py reset corpus --noinput
python2 manage.py reset evaluation --noinput
python2 manage.py syncdb

# Languages
./esmt add language -i es -l Spanish -n Español
./esmt add language -i de -l German -n Deutsch
./esmt add language -i en -l English -n English
./esmt add language -i fr -l French -n Français
./esmt add language -i cs -l Czech -n Český

# Import source data and translations
for i in \
    /home/david/penguin/share/taraxu/evaluation-rounds/r2/xmlAppraise/uploaded/wmt11-cs_en-wmt11-ranking.beo.xml \
    ; do
        echo "Adding $i"
	./esmt run bin/importCorporaFromRankingXML-r2.py $i
done
