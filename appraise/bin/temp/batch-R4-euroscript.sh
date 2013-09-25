for SET in customer0_new customer0_reuse customer1 customer2_new
do
    for i in 'en-de',EN,DE 'de-es',DE,ES 'es-de',ES,DE 'de-fr',DE,FR 'fr-de',FR,DE
    do
        IFS=","
        set $i
        echo ./esmt add document /wizard/appraise/data/r4/euroscript/$SET'_'$1.src -l $2 --idfile /wizard/appraise/data/r4/euroscript/$SET'_'$1.ids
        echo ./esmt add corpus -i $SET-R4-$1 -l $2 $SET'_'$1.src

        for SYSTEM in moses lucy trados
        do
            echo ./esmt add translation -i $SET-R4-$1 -s $SYSTEM-R4 /wizard/appraise/data/r4/euroscript/$SET'_'$1.$SYSTEM -l $3
        done
        
        
        echo ./esmt add task -t ranking -c $SET-R4-$1  -s 'moses-r4,lucy-r4,trados-r4' -n "'Evaluation Round 4: Ranking evaluation task for $1, $SET'" -u euroscript-R4-$1 -l $3 -R
        echo ./esmt add task -t select-and-post-edit -c $SET-R4-$1 -s moses-r4,lucy-r4,trados-r4 -n "'Evaluation Round 4: Select and post-edit task task for $1, $SET'" -u euroscript-R4-$1 -l $3 -R
    done
done
