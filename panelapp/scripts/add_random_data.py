import random
from beeprint import pp
from django.db import transaction
from accounts.models import Reviewer
from psycopg2.extras import NumericRange
from panels.models import Region, STR, GenePanelEntrySnapshot, GenePanelSnapshot, Evaluation, Gene, Evidence


def get_random_active_panel():
    return GenePanelSnapshot.objects.get_active(all=True, internal=True, superpanel=False).order_by('?').first()


def random_gene():
    return Gene.objects.order_by('?').first()


def random_str():
    return STR.objects.order_by('?').first()


def random_region():
    return Region.objects.order_by('?').first()


def get_random_words(length=3):
    return [random.choice(words) for _ in range(length)]


def get_random_sentences(length=3):
    return [' '.join(get_random_words()) for _ in range(length)]


def random_gene_data(gene):
    return {
        "gene": gene,
        "sources": Evidence.OTHER_SOURCES[0],
        "phenotypes": get_random_sentences(),
        "rating": random.choice([Evaluation.RATINGS.AMBER, Evaluation.RATINGS.GREEN, Evaluation.RATINGS.RED]),
        "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][random.randint(1, 12)][0],
        "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][random.randint(1, 2)][0],
        "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        "current_diagnostic": False
    }


def random_region_data(region):
    return {
        "gene": region.gene_core if hasattr(region, 'gene_core') else None,
        'chromosome': str(random.randint(1, 22)),
        'position_37': NumericRange(random.randint(1, 20000), random.randint(20001, 40000)),
        'position_38': NumericRange(random.randint(1, 20000), random.randint(20001, 40000)),
        'haploinsufficiency_score': random.choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
        'triplosensitivity_score': random.choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
        'required_overlap_percentage': random.randint(0, 100),
        'moi': [x for x in Evaluation.MODES_OF_INHERITANCE][random.randint(1, 12)][0],
        'penetrance': 'Incomplete',
        "publications": get_random_sentences(),
        "phenotypes": get_random_sentences(),
        "rating": random.choice([Evaluation.RATINGS.AMBER, Evaluation.RATINGS.GREEN, Evaluation.RATINGS.RED]),
        "comments": ' '.join(get_random_sentences()),
        'sources': [],
        "current_diagnostic": True,
        "type_of_variants": Region.VARIANT_TYPES.small,
    }


def random_str_data(data_str):
    return {
        'name': ' '.join(get_random_words(1)),
        'chromosome': str(random.randint(1, 22)),
        'position_37': NumericRange(random.randint(1, 20000), random.randint(20001, 40000)),
        'position_38': NumericRange(random.randint(1, 20000), random.randint(20001, 40000)),
        'repeated_sequence': ''.join(random.choice(['A', 'T', 'C', 'G']) for _ in range(random.randint(5, 20))),
        'normal_repeats': random.randint(1,5),
        'pathogenic_repeats': random.randint(6,15),
        "gene": data_str.gene_core if hasattr(data_str, 'gene_core') else None,
        "sources": Evidence.ALL_SOURCES[random.randint(0, 9)],
        "publications": get_random_sentences(),
        "phenotypes": get_random_sentences(),
        "rating": random.choice([Evaluation.RATINGS.AMBER, Evaluation.RATINGS.GREEN, Evaluation.RATINGS.RED]),
        "comments": ' '.join(get_random_sentences()),
        "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][random.randint(1, 12)][0],
        "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        "current_diagnostic": True
    }


def random_evaluation_data(user):
    return {
        "source": Evidence.ALL_SOURCES[random.randint(0, 9)],
        "phenotypes": get_random_sentences(),
        "publications": [],
        "rating": random.choice([Evaluation.RATINGS.AMBER, Evaluation.RATINGS.GREEN, Evaluation.RATINGS.RED]),
        "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][random.randint(1, 12)][0],
        "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][random.randint(1, 2)][0],
        "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        "current_diagnostic": False
    }


def add_some_entropy(gps):
    t = random.choice(['gene', 'str', 'region', 'evaluation', 'version'])

    print(gps, t)

    user = Reviewer.objects.filter(user_type=Reviewer.TYPES.GEL).order_by('?').first().user

    if t == 'gene':
        gene = random_gene()
        gene_symbol = gene.gene_symbol
        if gps.has_gene(gene_symbol):
            if random.randint(0, 1):
                gps.update_gene(user, gene_symbol, random_gene_data(gene))
            else:
                gps.delete_gene(gene_symbol, user=user)
        else:
            gps.add_gene(user, gene_symbol, random_gene_data(gene))
    elif t == 'str':
        str_item = random_str()
        random_data = random_str_data(str_item)
        if gps.has_str(str_item.name):
            if random.randint(0, 1):
                gps.update_str(user, str_item.name, random_data)
            else:
                gps.delete_str(str_item.name, user=user)
        else:
            gps.add_str(user, str_item.name, random_data)
    elif t == 'region':
        region = random_region()
        if gps.has_region(region.name):
            if random.randint(0, 1):
                gps.update_region(user, region.name, random_region_data(region))
            else:
                gps.delete_region(region.name, user=user)
        else:
            gps.add_region(user, region.name, random_region_data(region))
    elif t == 'evaluation':
        if gps.get_all_entities_extra:
            item = random.choice(gps.get_all_entities_extra)
            item.update_evaluation(user, random_evaluation_data(user))
    elif t == 'version':
        gps.increment_version()


def process(iterations=100):
    with transaction.atomic():
        print('Staring', 1000, 'iterations')
        for _ in range(iterations):
            gps = GenePanelSnapshot.objects.get_active(all=True, internal=True, superpanels=False).order_by('?').first()
            add_some_entropy(gps)

        print('Done')


words = [
    'ability',
    'able',
    'about',
    'above',
    'accept',
    'according',
    'account',
    'across',
    'act',
    'action',
    'activity',
    'actually',
    'add',
    'address',
    'administration',
    'admit',
    'adult',
    'affect',
    'after',
    'again',
    'against',
    'age',
    'agency',
    'agent',
    'ago',
    'agree',
    'agreement',
    'ahead',
    'air',
    'all',
    'allow',
    'almost',
    'alone',
    'along',
    'already',
    'also',
    'although',
    'always',
    'American',
    'among',
    'amount',
    'analysis',
    'and',
    'animal',
    'another',
    'answer',
    'any',
    'anyone',
    'anything',
    'appear',
    'apply',
    'approach',
    'area',
    'argue',
    'arm',
    'around',
    'arrive',
    'art',
    'article',
    'artist',
    'as',
    'ask',
    'assume',
    'at',
    'attack',
    'attention',
    'attorney',
    'audience',
    'author',
    'authority',
    'available',
    'avoid',
    'away',
    'baby',
    'back',
    'bad',
    'bag',
    'ball',
    'bank',
    'bar',
    'base',
    'be',
    'beat',
    'beautiful',
    'because',
    'become',
    'bed',
    'before',
    'begin',
    'behavior',
    'behind',
    'believe',
    'benefit',
    'best',
    'better',
    'between',
    'beyond',
    'big',
    'bill',
    'billion',
    'bit',
    'black',
    'blood',
    'blue',
    'board',
    'body',
    'book',
    'born',
    'both',
    'box',
    'boy',
    'break',
    'bring',
    'brother',
    'budget',
    'build',
    'building',
    'business',
    'but',
    'buy',
    'by',
    'call',
    'camera',
    'campaign',
    'can',
    'cancer',
    'candidate',
    'capital',
    'car',
    'card',
    'care',
    'career',
    'carry',
    'case',
    'catch',
    'cause',
    'cell',
    'center',
    'central',
    'century',
    'certain',
    'certainly',
    'chair',
    'challenge',
    'chance',
    'change',
    'character',
    'charge',
    'check',
    'child',
    'choice',
    'choose',
    'church',
    'citizen',
    'city',
    'civil',
    'claim',
    'class',
    'clear',
    'clearly',
    'close',
    'coach',
    'cold',
    'collection',
    'college',
    'color',
    'come',
    'commercial',
    'common',
    'community',
    'company',
    'compare',
    'computer',
    'concern',
    'condition',
    'conference',
    'Congress',
    'consider',
    'consumer',
    'contain',
    'continue',
    'control',
    'cost',
    'could',
    'country',
    'couple',
    'course',
    'court',
    'cover',
    'create',
    'crime',
    'cultural',
    'culture',
    'cup',
    'current',
    'customer',
    'cut',
    'dark',
    'data',
    'daughter',
    'day',
    'dead',
    'deal',
    'death',
    'debate',
    'decade',
    'decide',
    'decision',
    'deep',
    'defense',
    'degree',
    'Democrat',
    'democratic',
    'describe',
    'design',
    'despite',
    'detail',
    'determine',
    'develop',
    'development',
    'die',
    'difference',
    'different',
    'difficult',
    'dinner',
    'direction',
    'director',
    'discover',
    'discuss',
    'discussion',
    'disease',
    'do',
    'doctor',
    'dog',
    'door',
    'down',
    'draw',
    'dream',
    'drive',
    'drop',
    'drug',
    'during',
    'each',
    'early',
    'east',
    'easy',
    'eat',
    'economic',
    'economy',
    'edge',
    'education',
    'effect',
    'effort',
    'eight',
    'either',
    'election',
    'else',
    'employee',
    'end',
    'energy',
    'enjoy',
    'enough',
    'enter',
    'entire',
    'environment',
    'environmental',
    'especially',
    'establish',
    'even',
    'evening',
    'event',
    'ever',
    'every',
    'everybody',
    'everyone',
    'everything',
    'evidence',
    'exactly',
    'example',
    'executive',
    'exist',
    'expect',
    'experience',
    'expert',
    'explain',
    'eye',
    'face',
    'fact',
    'factor',
    'fail',
    'fall',
    'family',
    'far',
    'fast',
    'father',
    'fear',
    'federal',
    'feel',
    'feeling',
    'few',
    'field',
    'fight',
    'figure',
    'fill',
    'film',
    'final',
    'finally',
    'financial',
    'find',
    'fine',
    'finger',
    'finish',
    'fire',
    'firm',
    'first',
    'fish',
    'five',
    'floor',
    'fly',
    'focus',
    'follow',
    'food',
    'foot',
    'for',
    'force',
    'foreign',
    'forget',
    'form',
    'former',
    'forward',
    'four',
    'free',
    'friend',
    'from',
    'front',
    'full',
    'fund',
    'future',
    'game',
    'garden',
    'gas',
    'general',
    'generation',
    'get',
    'girl',
    'give',
    'glass',
    'go',
    'goal',
    'good',
    'government',
    'great',
    'green',
    'ground',
    'group',
    'grow',
    'growth',
    'guess',
    'gun',
    'guy',
    'hair',
    'half',
    'hand',
    'hang',
    'happen',
    'happy',
    'hard',
    'have',
    'he',
    'head',
    'health',
    'hear',
    'heart',
    'heat',
    'heavy',
    'help',
    'her',
    'here',
    'herself',
    'high',
    'him',
    'himself',
    'his',
    'history',
    'hit',
    'hold',
    'home',
    'hope',
    'hospital',
    'hot',
    'hotel',
    'hour',
    'house',
    'how',
    'however',
    'huge',
    'human',
    'hundred',
    'husband',
    'I',
    'idea',
    'identify',
    'if',
    'image',
    'imagine',
    'impact',
    'important',
    'improve',
    'in',
    'include',
    'including',
    'increase',
    'indeed',
    'indicate',
    'individual',
    'industry',
    'information',
    'inside',
    'instead',
    'institution',
    'interest',
    'interesting',
    'international',
    'interview',
    'into',
    'investment',
    'involve',
    'issue',
    'it',
    'item',
    'its',
    'itself',
    'job',
    'join',
    'just',
    'keep',
    'key',
    'kid',
    'kill',
    'kind',
    'kitchen',
    'know',
    'knowledge',
    'land',
    'language',
    'large',
    'last',
    'late',
    'later',
    'laugh',
    'law',
    'lawyer',
    'lay',
    'lead',
    'leader',
    'learn',
    'least',
    'leave',
    'left',
    'leg',
    'legal',
    'less',
    'let',
    'letter',
    'level',
    'lie',
    'life',
    'light',
    'like',
    'likely',
    'line',
    'list',
    'listen',
    'little',
    'live',
    'local',
    'long',
    'look',
    'lose',
    'loss',
    'lot',
    'love',
    'low',
    'machine',
    'magazine',
    'main',
    'maintain',
    'major',
    'majority',
    'make',
    'man',
    'manage',
    'management',
    'manager',
    'many',
    'market',
    'marriage',
    'material',
    'matter',
    'may',
    'maybe',
    'me',
    'mean',
    'measure',
    'media',
    'medical',
    'meet',
    'meeting',
    'member',
    'memory',
    'mention',
    'message',
    'method',
    'middle',
    'might',
    'military',
    'million',
    'mind',
    'minute',
    'miss',
    'mission',
    'model',
    'modern',
    'moment',
    'money',
    'month',
    'more',
    'morning',
    'most',
    'mother',
    'mouth',
    'move',
    'movement',
    'movie',
    'Mr',
    'Mrs',
    'much',
    'music',
    'must',
    'my',
    'myself',
    'name',
    'nation',
    'national',
    'natural',
    'nature',
    'near',
    'nearly',
    'necessary',
    'need',
    'network',
    'never',
    'new',
    'news',
    'newspaper',
    'next',
    'nice',
    'night',
    'no',
    'none',
    'nor',
    'north',
    'not',
    'note',
    'nothing',
    'notice',
    'now',
    'nt',
    'number',
    'occur',
    'of',
    'off',
    'offer',
    'office',
    'officer',
    'official',
    'often',
    'oh',
    'oil',
    'ok',
    'old',
    'on',
    'once',
    'one',
    'only',
    'onto',
    'open',
    'operation',
    'opportunity',
    'option',
    'or',
    'order',
    'organization',
    'other',
    'others',
    'our',
    'out',
    'outside',
    'over',
    'own',
    'owner',
    'page',
    'pain',
    'painting',
    'paper',
    'parent',
    'part',
    'participant',
    'particular',
    'particularly',
    'partner',
    'party',
    'pass',
    'past',
    'patient',
    'pattern',
    'pay',
    'peace',
    'people',
    'per',
    'perform',
    'performance',
    'perhaps',
    'period',
    'person',
    'personal',
    'phone',
    'physical',
    'pick',
    'picture',
    'piece',
    'place',
    'plan',
    'plant',
    'play',
    'player',
    'PM',
    'point',
    'police',
    'policy',
    'political',
    'politics',
    'poor',
    'popular',
    'population',
    'position',
    'positive',
    'possible',
    'power',
    'practice',
    'prepare',
    'present',
    'president',
    'pressure',
    'pretty',
    'prevent',
    'price',
    'private',
    'probably',
    'problem',
    'process',
    'produce',
    'product',
    'production',
    'professional',
    'professor',
    'program',
    'project',
    'property',
    'protect',
    'prove',
    'provide',
    'public',
    'pull',
    'purpose',
    'push',
    'put',
    'quality',
    'question',
    'quickly',
    'quite',
    'race',
    'radio',
    'raise',
    'range',
    'rate',
    'rather',
    'reach',
    'read',
    'ready',
    'real',
    'reality',
    'realize',
    'really',
    'reason',
    'receive',
    'recent',
    'recently',
    'recognize',
    'record',
    'red',
    'reduce',
    'reflect',
    'region',
    'relate',
    'relationship',
    'religious',
    'remain',
    'remember',
    'remove',
    'report',
    'represent',
    'Republican',
    'require',
    'research',
    'resource',
    'respond',
    'response',
    'responsibility',
    'rest',
    'result',
    'return',
    'reveal',
    'rich',
    'right',
    'rise',
    'risk',
    'road',
    'rock',
    'role',
    'room',
    'rule',
    'run',
    'safe',
    'same',
    'save',
    'say',
    'scene',
    'school',
    'science',
    'scientist',
    'score',
    'sea',
    'season',
    'seat',
    'second',
    'section',
    'security',
    'see',
    'seek',
    'seem',
    'sell',
    'send',
    'senior',
    'sense',
    'series',
    'serious',
    'serve',
    'service',
    'set',
    'seven',
    'several',
    'sex',
    'sexual',
    'shake',
    'share',
    'she',
    'shoot',
    'short',
    'shot',
    'should',
    'shoulder',
    'show',
    'side',
    'sign',
    'significant',
    'similar',
    'simple',
    'simply',
    'since',
    'sing',
    'single',
    'sister',
    'sit',
    'site',
    'situation',
    'six',
    'size',
    'skill',
    'skin',
    'small',
    'smile',
    'so',
    'social',
    'society',
    'soldier',
    'some',
    'somebody',
    'someone',
    'something',
    'sometimes',
    'son',
    'song',
    'soon',
    'sort',
    'sound',
    'source',
    'south',
    'southern',
    'space',
    'speak',
    'special',
    'specific',
    'speech',
    'spend',
    'sport',
    'spring',
    'staff',
    'stage',
    'stand',
    'standard',
    'star',
    'start',
    'state',
    'statement',
    'station',
    'stay',
    'step',
    'still',
    'stock',
    'stop',
    'store',
    'story',
    'strategy',
    'street',
    'strong',
    'structure',
    'student',
    'study',
    'stuff',
    'style',
    'subject',
    'success',
    'successful',
    'such',
    'suddenly',
    'suffer',
    'suggest',
    'summer',
    'support',
    'sure',
    'surface',
    'system',
    'table',
    'take',
    'talk',
    'task',
    'tax',
    'teach',
    'teacher',
    'team',
    'technology',
    'television',
    'tell',
    'ten',
    'tend',
    'term',
    'test',
    'than',
    'thank',
    'that',
    'the',
    'their',
    'them',
    'themselves',
    'then',
    'theory',
    'there',
    'these',
    'they',
    'thing',
    'think',
    'third',
    'this',
    'those',
    'though',
    'thought',
    'thousand',
    'threat',
    'three',
    'through',
    'throughout',
    'throw',
    'thus',
    'time',
    'to',
    'today',
    'together',
    'tonight',
    'too',
    'top',
    'total',
    'tough',
    'toward',
    'town',
    'trade',
    'traditional',
    'training',
    'travel',
    'treat',
    'treatment',
    'tree',
    'trial',
    'trip',
    'trouble',
    'true',
    'truth',
    'try',
    'turn',
    'TV',
    'two',
    'type',
    'under',
    'understand',
    'unit',
    'until',
    'up',
    'upon',
    'us',
    'use',
    'usually',
    'value',
    'various',
    'very',
    'victim',
    'view',
    'violence',
    'visit',
    'voice',
    'vote',
    'wait',
    'walk',
    'wall',
    'want',
    'war',
    'watch',
    'water',
    'way',
    'we',
    'weapon',
    'wear',
    'week',
    'weight',
    'well',
    'west',
    'western',
    'what',
    'whatever',
    'when',
    'where',
    'whether',
    'which',
    'while',
    'white',
    'who',
    'whole',
    'whom',
    'whose',
    'why',
    'wide',
    'wife',
    'will',
    'win',
    'wind',
    'window',
    'wish',
    'with',
    'within',
    'without',
    'woman',
    'wonder',
    'word',
    'work',
    'worker',
    'world',
    'worry',
    'would',
    'write',
    'writer',
    'wrong',
    'yard',
    'yeah',
    'year',
    'yes',
    'yet',
    'you',
    'young',
    'your',
    'yourself',
]

process()
