import corpus.models
from django.contrib import admin

class SentenceInline(admin.TabularInline):
    model = corpus.models.SourceSentence
    #fields = ('customId', 'text'),
    extra = 0

class SourceDocumentAdmin(admin.ModelAdmin):
    model = corpus.models.SourceDocument
    #fields = ('id', 'sourceLanguage'),
    inlines = [SentenceInline]
    classes = ['collapse']

    
class FeatureInline(admin.TabularInline):
    model = corpus.models.Feature
    extra = 0

class FeatureSetAdmin(admin.ModelAdmin):
    model = corpus.models.FeatureSet
    inlines = [FeatureInline]    
    classes = ['collapse']

admin.site.register(corpus.models.Language)
admin.site.register(corpus.models.SourceDocument, SourceDocumentAdmin)
admin.site.register(corpus.models.Corpus)
admin.site.register(corpus.models.TranslatedDocument)
admin.site.register(corpus.models.SourceSentence)
admin.site.register(corpus.models.Translation)

admin.site.register(corpus.models.TranslationSystem)
admin.site.register(corpus.models.MonoAnalysisSystem)
admin.site.register(corpus.models.BiAnalysisSystem)
admin.site.register(corpus.models.FeatureSet, FeatureSetAdmin)
admin.site.register(corpus.models.Feature)
admin.site.register(corpus.models.FeatureValue)

