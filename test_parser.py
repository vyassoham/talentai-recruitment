from services.ai.cv_parser import CVParser
text = '''
JAGDISH PRAJAPATI
Email: jagdish.prajapati@gmail.com
Phone: +91 9876543210
Software Engineer with 5 years of experience.
Skills: Python, Redis, Distributed Systems
'''
parser = CVParser()
res = parser.parse_cv(text)
print("Email:", res.email)
print("Phone:", res.phone)
