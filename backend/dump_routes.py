import sys, json
sys.path.insert(0, 'backend')
from app.main import create_app
app = create_app()
openapi = app.openapi()

tag_to_file = {
    'Authentication': 'auth.py',
    'Skills': 'skills.py',
    'Courses': 'courses.py',
    'Course Skills': 'course_skills.py',
    'Job Postings': 'job_postings.py',
    'Job Skills': 'job_skills.py',
    'User Skills': 'user_skills.py',
    'Jobs': 'routes_jobs.py',
    'Employers': 'routes_employers.py',
    'ML Intelligence': 'routes_ml.py',
    'Career Roles': 'routes_roles.py',
    'Students': 'routes_students.py',
    'Root': 'main.py',
    'Health': 'main.py'
}

lines = []
lines.append('| Method | Route | File | Auth Required | Request Schema | Response Schema |')
lines.append('|---|---|---|---|---|---|')

for path, methods in sorted(openapi.get('paths', {}).items()):
    for method, spec in sorted(methods.items()):
        tags = spec.get('tags', [])
        tag = tags[0] if tags else 'Root'
        file_name = tag_to_file.get(tag, 'unknown.py')
        has_auth = 'security' in spec and len(spec['security']) > 0
        req_schema = '-'
        if 'requestBody' in spec:
            content = spec['requestBody'].get('content', {})
            for ctype, cdata in content.items():
                schema = cdata.get('schema', {})
                if '$ref' in schema:
                    req_schema = schema['$ref'].split('/')[-1]
                else:
                    req_schema = schema.get('type', 'body')
        resp_schema = '-'
        resps = spec.get('responses', {})
        for code in ['200', '201']:
            if code in resps:
                content = resps[code].get('content', {})
                for ctype, cdata in content.items():
                    schema = cdata.get('schema', {})
                    if '$ref' in schema:
                        resp_schema = schema['$ref'].split('/')[-1]
                    elif 'items' in schema and '$ref' in schema['items']:
                        resp_schema = f"List[{schema['items']['$ref'].split('/')[-1]}]"
                    else:
                        resp_schema = schema.get('type', 'Any')
                break
        lines.append(f'| {method.upper()} | {path} | {file_name} | {"Yes" if has_auth else "No"} | {req_schema} | {resp_schema} |')

output_str = "\n".join(lines)
with open("backend_routes_table.txt", "w", encoding="utf-8") as f:
    f.write(output_str)

print(f"Written {len(lines)-2} routes to backend_routes_table.txt")
