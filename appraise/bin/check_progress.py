import sys
import datetime
from evaluation.models import *
from django.db.models import Sum

try:
    keyword = sys.argv[1]
except:
    print "Please provide a keyword that should be part of the Task name"

items_total = 0
results_total = 0
users_all = []

task_types = [RankingTask, QualityTask, SelectAndPostEditTask, PostEditAllTask]
for task_type in task_types:
    print "\n", task_type.__name__, "\n-------------"
    tasks = task_type.objects.filter(task_name__contains=keyword, active=True)

    items_tasktype = 0
    results_tasktype = 0

    for task in tasks:
        users = task.users.all()
        users_all.extend(users)
        userstats_string = []
        for user in users:
            itemcount = EvaluationItem.objects.filter(task=task).count()
            items_tasktype += itemcount

            resultcount = NewEvaluationResult.objects.filter(item__task=task, user=user).count()
            results_tasktype += resultcount
            
            try:
                percentage = round((100.00*resultcount)/itemcount, 2)
            except ZeroDivisionError:
                percentage = 0.00
            userstats_string.append("{:.2f}%\t{}/{}".format(percentage,resultcount,itemcount))

        #task stats, with one column per user
        print "{}\t\t{}".format(task.task_name.ljust(90)[:90],"\t".join(userstats_string))

    #task type stats
    try:
        percentage = round((100.00*results_tasktype)/items_tasktype, 2)
    except ZeroDivisionError:
                percentage = 0.00
    print "------------------\nTask Total: \t\t {:.2f}%\t{}/{}".format(percentage,results_tasktype,items_tasktype)
    items_total += items_tasktype
    results_total += results_tasktype

print "\n\nUsers\n-----"       
discrete_users = set(users_all)
seconds_total = 0

for user in discrete_users:
    resultitems = NewEvaluationResult.objects.filter(item__task__task_name__contains=keyword, user=user)
    try:
        seconds = int(resultitems.aggregate(Sum('duration'))['duration__sum'])
    except:
        seconds = 0
    seconds_total += seconds
    duration = int(round(seconds/3600.00,0))
    resultcount = resultitems.count()
    itemcount = EvaluationItem.objects.filter(task__task_name__contains=keyword, task__users=user).count()
    percentage = round((100.00*resultcount)/itemcount, 2)
    print "{}\t{} hrs\t{:.2f}%\t{}/{}".format(user.username.ljust(20)[:20],duration,percentage,resultcount,itemcount)

print "\n\nTotal\n-----"
duration_total = int(round(seconds_total/3600.00,0))
percentage = round((100.00*results_total)/items_total, 2)
print "{}hrs\t{:.2f}%\t{}/{}".format(duration_total,percentage,results_total,items_total)
