'''
Created on Feb 7, 2014

@author: Eleftherios Avramidis
'''

from io_utils.sax.cejcml import CEJcmlReader
from corpus.models import SourceSentence, Feature, FeatureValue, Translation


class FeaturesImporter:
    
    def __init__(self):
        self.features = {} 
        
        
    def get_simplesentence_featurevalues(self, simplesentence, sentenceobject):
        attributes = simplesentence.get_attributes()
        featurevalues = []
        for key, value in attributes.iteritems():
            #cache feature in memory to reduce db lookups
            feature = self.features.setdefault(key, Feature.objects.get_or_create(name=key))
            featurevalue = FeatureValue(feature=feature, sentence=sentenceobject, value=value)
            featurevalues.append(featurevalue)

    def get_parallelsentence_featurevalues(self, parallelsentence):
        featurevalues = []
        attributes = parallelsentence.get_attributes()
        sentenceobject = SourceSentence.objects.get(custom_id=attributes['id'], 
                                                      document=attributes['testset'],
                                                      document__language__name=attributes['langsrc'].upper())
        sourcesentence = parallelsentence.get_source()        
        featurevalues.extend(self.get_simplesentence_featurevalues(sourcesentence, sentenceobject))
        
        for translation in parallelsentence.get_translations():
            
            translationobject = Translation.objects.get(source_sentence=sentenceobject, document__translateddocument__translation_system__name=translation.get_attribute("system"))
            featurevalues.extend(self.get_simplesentence_featurevalues(translation, translationobject))
            
        return featurevalues
        
        
    
    
    
    def import_features_from_file(self, filename, bulk=True):
        """
        Import sentences from given JCML file into the django database schema
        @filename: filename incl. path of a jcml XML file to read from
        @type: string 
        @param bulk: if TRUE read all of them into the memory  and then send one bulk
         request to the Django server
        @type bulk: boolean
        """
        
        reader = CEJcmlReader(filename)
        dataset = reader.get_dataset()
        featurevalues = []
        
        if bulk:
            for parallelsentence in dataset:
                featurevalues.extend(self.get_parallelsentence_featurevalues(parallelsentence))            
            FeatureValue.objects.bulk_create(featurevalues)
        
        if not bulk:
            for parallelsentence in dataset:
                featurevalues = self.get_parallelsentence_featurevalues(parallelsentence)
                FeatureValue.objects.bulk_create(featurevalues)

if __name__ == '__main__':
    pass
