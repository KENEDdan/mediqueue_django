from django.core.management.base import BaseCommand
from apps.clinics.models import Specialization

SPECIALIZATIONS = [
    {
        'name': 'General Practice',
        'icon': '🩺',
        'description': 'General Practitioners are your first point of contact for any health concern. They diagnose, treat, and manage a wide range of illnesses and coordinate your care with specialists when needed.',
        'common_conditions': 'Common cold, flu, fever, infections, hypertension, diabetes, routine check-ups, vaccinations, minor injuries, fatigue',
        'example_symptoms': 'Fever, cough, sore throat, body aches, headache, tiredness, runny nose, stomach ache, general feeling of being unwell',
        'when_to_visit': 'When you are sick but unsure which specialist to see. Always start here if you are not sure — the GP will refer you to the right specialist.',
    },
    {
        'name': 'Cardiology',
        'icon': '❤️',
        'description': 'Cardiologists specialise in the heart and blood vessels. They diagnose and treat diseases of the cardiovascular system including heart attacks, irregular heartbeats, and heart failure.',
        'common_conditions': 'High blood pressure, heart attack, heart failure, irregular heartbeat (arrhythmia), chest pain, coronary artery disease, heart valve disease, stroke',
        'example_symptoms': 'Chest pain or tightness, shortness of breath, rapid or irregular heartbeat, swollen legs or ankles, dizziness, fainting, excessive fatigue on exertion',
        'when_to_visit': 'If you have chest pain, shortness of breath, palpitations, or a family history of heart disease. Also if your GP has referred you for a heart-related concern.',
    },
    {
        'name': 'Pediatrics',
        'icon': '👶',
        'description': 'Paediatricians specialise in the health and medical care of infants, children, and teenagers from birth up to age 18.',
        'common_conditions': 'Growth and development concerns, childhood infections, asthma, allergies, vaccinations, malnutrition, ear infections, childhood diabetes',
        'example_symptoms': 'Fever in a child, persistent cough in children, rashes, poor weight gain, delayed milestones, frequent ear infections, vomiting and diarrhoea in infants',
        'when_to_visit': 'For any health concern involving a baby, child, or teenager. Routine well-child visits, vaccinations, or when your child is sick.',
    },
    {
        'name': 'Dermatology',
        'icon': '🧴',
        'description': 'Dermatologists specialise in conditions affecting the skin, hair, and nails. They treat everything from acne to skin cancer.',
        'common_conditions': 'Acne, eczema, psoriasis, skin cancer, fungal infections, rashes, warts, vitiligo, hair loss, nail infections, allergic reactions on skin',
        'example_symptoms': 'Rash, itchy skin, unusual moles or growths, persistent acne, dry or scaly patches, hair thinning or loss, discoloured or brittle nails, skin peeling',
        'when_to_visit': 'When you have a skin, hair, or nail problem that persists for more than 2 weeks, is getting worse, is spreading, or you notice a new or changing mole.',
    },
    {
        'name': 'Orthopedics',
        'icon': '🦴',
        'description': 'Orthopaedic specialists focus on the musculoskeletal system — bones, joints, ligaments, tendons, and muscles. They treat injuries, arthritis, and deformities.',
        'common_conditions': 'Fractures, sports injuries, arthritis, back pain, scoliosis, hip and knee replacement, carpal tunnel syndrome, torn ligaments, shoulder pain',
        'example_symptoms': 'Bone or joint pain, swollen or stiff joints, difficulty walking or moving limbs, back or neck pain, numbness or tingling in hands or feet, muscle weakness, injury from a fall or accident',
        'when_to_visit': 'After a bone or joint injury, if you have persistent joint pain, difficulty moving, or your GP has referred you for a musculoskeletal concern.',
    },
    {
        'name': 'Neurology',
        'icon': '🧠',
        'description': 'Neurologists specialise in disorders of the brain, spinal cord, and nerves. They diagnose and treat conditions affecting the nervous system.',
        'common_conditions': 'Stroke, epilepsy, migraines, Parkinson\'s disease, multiple sclerosis, dementia, Alzheimer\'s disease, neuropathy, brain tumours',
        'example_symptoms': 'Severe or recurring headaches, dizziness or balance problems, memory loss or confusion, seizures, weakness or numbness on one side of the body, tremors, vision problems, difficulty speaking',
        'when_to_visit': 'If you have unexplained headaches, memory problems, weakness, seizures, or any symptoms involving your brain or nervous system.',
    },
    {
        'name': 'Gynecology',
        'icon': '🌸',
        'description': 'Gynaecologists specialise in the female reproductive system. They provide care for women\'s reproductive health from puberty through menopause and beyond.',
        'common_conditions': 'Menstrual disorders, PCOS, fibroids, endometriosis, ovarian cysts, sexually transmitted infections, menopause, fertility issues, cervical cancer screening',
        'example_symptoms': 'Irregular, painful or heavy periods, pelvic pain or pressure, abnormal vaginal discharge, pain during intercourse, missed periods, vaginal itching or burning, bleeding after menopause',
        'when_to_visit': 'For any concern about your menstrual cycle, reproductive health, pelvic pain, or for routine Pap smear and STI screening. Annually recommended for all women.',
    },
    {
        'name': 'Ophthalmology',
        'icon': '👁️',
        'description': 'Ophthalmologists specialise in eye health and vision care. They diagnose and treat eye diseases and perform eye surgery.',
        'common_conditions': 'Cataracts, glaucoma, macular degeneration, diabetic retinopathy, dry eye syndrome, strabismus, retinal detachment, conjunctivitis',
        'example_symptoms': 'Blurred or cloudy vision, sudden vision loss, eye pain, redness or discharge, seeing floaters or flashes of light, double vision, sensitivity to light, difficulty seeing at night',
        'when_to_visit': 'If you notice any change in your vision, eye pain, redness, or discharge. Also for routine annual eye checks especially if you wear glasses or have diabetes.',
    },
    {
        'name': 'ENT (Ear, Nose & Throat)',
        'icon': '👂',
        'description': 'ENT specialists (Otolaryngologists) treat conditions affecting the ears, nose, throat, head, and neck. They handle everything from hearing loss to sinus infections.',
        'common_conditions': 'Sinusitis, tonsillitis, hearing loss, ear infections, sleep apnoea, nasal polyps, voice disorders, thyroid disorders, vertigo, tinnitus',
        'example_symptoms': 'Persistent sore throat, difficulty swallowing, blocked or runny nose, ear pain or ringing, hearing loss, hoarseness, snoring, dizziness, lump in neck or throat',
        'when_to_visit': 'When you have recurring ear, nose, or throat infections; hearing problems; difficulty breathing through your nose; or a lump in your neck.',
    },
    {
        'name': 'Psychiatry',
        'icon': '🧘',
        'description': 'Psychiatrists are medical doctors specialising in mental health. They diagnose, treat, and prevent mental, emotional, and behavioural disorders.',
        'common_conditions': 'Depression, anxiety disorders, bipolar disorder, schizophrenia, PTSD, OCD, eating disorders, addiction, ADHD, sleep disorders',
        'example_symptoms': 'Persistent sadness or hopelessness, excessive worry or fear, hearing or seeing things others don\'t, extreme mood swings, difficulty concentrating, suicidal thoughts, loss of interest in life, insomnia',
        'when_to_visit': 'When emotional or mental health issues interfere with daily life. You don\'t need a referral — seeking help is a sign of strength, not weakness.',
    },
    {
        'name': 'Dentistry',
        'icon': '🦷',
        'description': 'Dentists specialise in the diagnosis, prevention, and treatment of conditions affecting the teeth, gums, and mouth.',
        'common_conditions': 'Tooth decay, gum disease, tooth abscess, cavities, tooth extraction, root canal, teeth whitening, dental implants, braces, mouth ulcers',
        'example_symptoms': 'Toothache, sensitive teeth, bleeding or swollen gums, bad breath, loose teeth, pain when chewing, mouth sores that don\'t heal, jaw pain or clicking',
        'when_to_visit': 'Every 6 months for routine cleaning. Sooner if you have toothache, bleeding gums, swelling, or notice any changes in your mouth.',
    },
    {
        'name': 'Oncology',
        'icon': '🎗️',
        'description': 'Oncologists specialise in the diagnosis and treatment of cancer. They work with radiation, chemotherapy, immunotherapy, and surgery to treat all types of cancer.',
        'common_conditions': 'Breast cancer, lung cancer, colon cancer, prostate cancer, cervical cancer, leukaemia, lymphoma, skin cancer, liver cancer, brain tumours',
        'example_symptoms': 'Unexplained weight loss, persistent fatigue, unusual lumps or swellings, changes in a mole or skin growth, unexplained bleeding, persistent pain, chronic cough or hoarseness, difficulty swallowing',
        'when_to_visit': 'If you notice a persistent lump, unexplained weight loss, or any symptom that doesn\'t resolve after a few weeks. Early detection saves lives — don\'t wait.',
    },
    {
        'name': 'Urology',
        'icon': '🫘',
        'description': 'Urologists specialise in the urinary tract system and male reproductive organs. They treat conditions in both men and women affecting the kidneys, bladder, and urethra.',
        'common_conditions': 'Kidney stones, urinary tract infections, prostate problems, bladder issues, male infertility, erectile dysfunction, incontinence, kidney cancer',
        'example_symptoms': 'Frequent or painful urination, blood in urine, difficulty urinating, lower back or groin pain, incomplete bladder emptying, leaking urine, recurrent UTIs',
        'when_to_visit': 'When you have persistent problems with urination, blood in your urine, kidney stones, or any urological symptoms your GP has flagged.',
    },
    {
        'name': 'Endocrinology',
        'icon': '⚗️',
        'description': 'Endocrinologists specialise in hormones and the glands that produce them. They treat disorders of the thyroid, pancreas, adrenal glands, and other endocrine organs.',
        'common_conditions': 'Diabetes (Type 1 & 2), thyroid disorders, obesity, polycystic ovary syndrome (PCOS), osteoporosis, growth disorders, adrenal disorders, pituitary tumours',
        'example_symptoms': 'Unexplained weight gain or loss, excessive thirst or urination, fatigue, hair loss, feeling always hot or cold, irregular periods, poor concentration, brittle bones',
        'when_to_visit': 'If you have been diagnosed with diabetes or thyroid disease, or have symptoms suggesting a hormone imbalance that your GP wants investigated.',
    },
    {
        'name': 'Physiotherapy',
        'icon': '🏃',
        'description': 'Physiotherapists help patients recover movement and function after injury, surgery, or illness. They use exercise, manual therapy, and rehabilitation techniques.',
        'common_conditions': 'Sports injuries, post-surgery rehabilitation, stroke recovery, back and neck pain, joint pain, cerebral palsy, respiratory conditions, chronic pain management',
        'example_symptoms': 'Limited movement or stiffness, pain during movement, muscle weakness, recovery after surgery or stroke, poor balance, sports injuries, chronic back or neck pain',
        'when_to_visit': 'After surgery, injury, or stroke for rehabilitation. Also if you have chronic pain, poor posture, or movement problems affecting daily life.',
    },
    {
        'name': 'Internal Medicine',
        'icon': '🔬',
        'description': 'Internists are specialists in adult medicine who manage complex, chronic conditions. They often serve as the primary doctor for adults with multiple health issues.',
        'common_conditions': 'Hypertension, diabetes, heart disease, COPD, kidney disease, liver disease, autoimmune diseases, complex multi-system disorders',
        'example_symptoms': 'Managing multiple chronic conditions, complex unexplained symptoms, fatigue, recurrent infections, abnormal blood test results requiring specialist interpretation',
        'when_to_visit': 'If you have multiple chronic conditions or complex symptoms that need a specialist in adult medicine to coordinate your overall care.',
    },
    {
        'name': 'Gastroenterology',
        'icon': '🫁',
        'description': 'Gastroenterologists specialise in the digestive system — oesophagus, stomach, intestines, liver, pancreas, and gallbladder.',
        'common_conditions': 'GERD (acid reflux), irritable bowel syndrome, Crohn\'s disease, ulcerative colitis, liver disease, gallstones, colon cancer, peptic ulcers, hepatitis',
        'example_symptoms': 'Persistent heartburn or acid reflux, abdominal pain, bloating, chronic diarrhoea or constipation, blood in stool, unexplained weight loss, difficulty swallowing, jaundice (yellow skin)',
        'when_to_visit': 'If you have persistent digestive issues, abdominal pain, or changes in bowel habits lasting more than a few weeks.',
    },
    {
        'name': 'Rheumatology',
        'icon': '🦾',
        'description': 'Rheumatologists specialise in autoimmune and inflammatory diseases affecting joints, muscles, and connective tissue.',
        'common_conditions': 'Rheumatoid arthritis, lupus, gout, Sjogren\'s syndrome, fibromyalgia, ankylosing spondylitis, vasculitis, scleroderma',
        'example_symptoms': 'Joint pain and swelling, morning stiffness, muscle pain, fatigue, skin rashes with joint problems, dry eyes or mouth, recurring joint inflammation',
        'when_to_visit': 'If you have persistent joint pain, swelling, and stiffness — especially if it\'s in multiple joints or associated with fatigue and skin changes.',
    },
    {
        'name': 'Obstetrics',
        'icon': '🤰',
        'description': 'Obstetricians specialise in pregnancy, childbirth, and postpartum care. They monitor both mother and baby throughout pregnancy and delivery.',
        'common_conditions': 'Prenatal care, high-risk pregnancy, gestational diabetes, pre-eclampsia, miscarriage, ectopic pregnancy, labour and delivery, postpartum care',
        'example_symptoms': 'Confirmed or suspected pregnancy, missed period, morning sickness, reduced fetal movement, vaginal bleeding during pregnancy, labour pains, high blood pressure in pregnancy',
        'when_to_visit': 'As soon as you confirm pregnancy or suspect you are pregnant. Regular antenatal visits are critical for mother and baby\'s health.',
    },
    {
        'name': 'Emergency Medicine',
        'icon': '🚨',
        'description': 'Emergency physicians handle acute, life-threatening conditions that require immediate attention.',
        'common_conditions': 'Heart attack, stroke, severe injuries, poisoning, severe allergic reactions, breathing difficulties, severe infections, trauma',
        'example_symptoms': 'Chest pain, difficulty breathing, sudden severe headache, loss of consciousness, severe bleeding, suspected broken bones, high fever with stiff neck, severe allergic reaction',
        'when_to_visit': 'For any condition that is life-threatening or requires immediate medical attention. Do not wait for an appointment — go directly to the emergency room.',
    },
]


class Command(BaseCommand):
    help = 'Load or update specializations with full descriptions'

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for spec_data in SPECIALIZATIONS:
            obj, is_new = Specialization.objects.update_or_create(
                name=spec_data['name'],
                defaults={
                    'icon':             spec_data['icon'],
                    'description':      spec_data['description'],
                    'common_conditions':spec_data['common_conditions'],
                    'example_symptoms': spec_data['example_symptoms'],
                    'when_to_visit':    spec_data['when_to_visit'],
                }
            )
            if is_new:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f'✅ Done — {created} created, {updated} updated. Total: {len(SPECIALIZATIONS)} specializations.'
        ))