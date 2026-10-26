"""A compact beginner-to-intermediate Hindi curriculum the tutor follows and tracks."""

LESSONS = [
    {
        "id": "01-vowels",
        "title": "Devanagari vowels (स्वर)",
        "goals": "Recognise and pronounce अ आ इ ई उ ऊ ए ऐ ओ औ and their matra forms (ा ि ी ु ू े ै ो ौ).",
    },
    {
        "id": "02-consonants",
        "title": "Consonants (व्यंजन) and reading syllables",
        "goals": "Read the consonant grid (क-वर्ग to प-वर्ग, य र ल व, श ष स ह), aspirated vs unaspirated, retroflex vs dental, simple conjuncts like क्ष त्र ज्ञ.",
    },
    {
        "id": "03-greetings",
        "title": "Greetings and introductions",
        "goals": "नमस्ते, आप कैसे हैं?, मेरा नाम ... है, मैं ... से हूँ, धन्यवाद, फिर मिलेंगे.",
    },
    {
        "id": "04-pronouns-hona",
        "title": "Pronouns and 'to be' (होना)",
        "goals": "मैं हूँ, तुम हो, आप हैं, वह है, हम/वे हैं; formality levels तू / तुम / आप.",
    },
    {
        "id": "05-numbers",
        "title": "Numbers 1-20 and telling the price",
        "goals": "एक से बीस तक; कितने का है?, ... रुपये.",
    },
    {
        "id": "06-gender",
        "title": "Noun gender and adjective agreement",
        "goals": "Masculine -आ / feminine -ई patterns, exceptions, अच्छा/अच्छी/अच्छे agreement.",
    },
    {
        "id": "07-postpositions",
        "title": "Postpositions (में, पर, को, से, का/की/के)",
        "goals": "Location, direction and possession; oblique case (लड़का -> लड़के में).",
    },
    {
        "id": "08-present-tense",
        "title": "Present habitual tense",
        "goals": "Verb stem + ता/ती/ते + है/हैं: मैं हिंदी बोलता हूँ / बोलती हूँ.",
    },
    {
        "id": "09-questions",
        "title": "Asking questions",
        "goals": "क्या, कौन, कहाँ, कब, क्यों, कैसे, कितना; yes/no questions with क्या.",
    },
    {
        "id": "10-past-tense",
        "title": "Past tense and the ने construction",
        "goals": "मैं गया / गई; transitive verbs with ने: मैंने खाना खाया.",
    },
    {
        "id": "11-future-tense",
        "title": "Future tense",
        "goals": "-ऊँगा/-एगा/-ओगे/-एँगे endings: मैं कल आऊँगा.",
    },
    {
        "id": "12-everyday",
        "title": "Everyday situations",
        "goals": "Food, shopping, directions, travel: मुझे ... चाहिए, ... कहाँ है?, बहुत महँगा है!",
    },
]

LESSON_IDS = {lesson["id"] for lesson in LESSONS}
