'''
Created on 27 Jul 2012

@author: elav01
'''

from django.contrib import admin
import eval.models

admin.site.register(eval.models.ErrorClass)
admin.site.register(eval.models.EvaluationCampaign)
admin.site.register(eval.models.EvaluationTask)
admin.site.register(eval.models.EvaluationItem)





 