'''
Created on 27 Jul 2012

@author: Patrick Bessler, David Vilar, Eleftherios Avramidis
'''

from django.db import models
from corpus.models import TranslatedDocument, SourceSentence, TranslationSystem 


"""
    Rule-based Selection mechanism
"""

class Rule(models.Model):
    rule_name = models.CharField(max_length=180)
    description = models.CharField(max_length=765)


class Publication(models.Model):
    project = models.ForeignKey(TranslatedDocument)
    rule = models.ForeignKey(Rule)
    created = models.DateTimeField()
    modified = models.DateTimeField()
    sentence = models.ForeignKey(SourceSentence)
    system = models.ForeignKey(TranslationSystem)

