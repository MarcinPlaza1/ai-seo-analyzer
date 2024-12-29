from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from functools import lru_cache

@lru_cache(maxsize=1)
def get_template_env():
    return Environment(
        loader=FileSystemLoader('app/templates'),
        autoescape=True
    )

async def generate_pdf_report(audit_data: dict) -> bytes:
    env = get_template_env()
    template = env.get_template('report.html')
    html_content = template.render(data=audit_data)
    
    return HTML(string=html_content).write_pdf() 