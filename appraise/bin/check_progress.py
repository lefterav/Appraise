import sys

from evaluation.models import *
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
            userstats_string.append("{:.2g}%\t{}/{}".format(percentage,resultcount,itemcount))

        #task stats, with one column per user
        print "{}\t{}\t".format(task.task_name.ljust(90)[:90],"\t".join(userstats_string))

    #task type stats
    try:
        percentage = round((100.00*results_tasktype)/items_tasktype, 2)
    except ZeroDivisionError:
                percentage = 0.00
    print "------------------\nTask Total: \t\t {:.2g}%\t{}/{}".format(percentage,results_tasktype,items_tasktype)
    items_total += items_tasktype
    results_total += results_tasktype

print "\n\nUsers\n-----"       
discrete_users = set(users_all)

for user in discrete_users:
    resultcount = NewEvaluationResult.objects.filter(item__task__task_name__contains=keyword, user=user).count()
    itemcount = EvaluationItem.objects.filter(task__task_name__contains=keyword, task__users=user).count()
    percentage = round((100.00*resultcount)/itemcount, 2)
    print "{}\t{:.2g}%\t{}/{}".format(user.username.ljust(20)[:20],percentage,resultcount,itemcount)

print "\n\nTotal\n-----"
percentage = round((100.00*results_total)/items_total, 2)
print "{:.2g}%\t{}/{}".format(percentage,results_total,items_total)
