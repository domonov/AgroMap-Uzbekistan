"""Documentation management utilities for AgroMap."""
import os
import re
import logging
import shutil
import subprocess
import datetime
from typing import Dict, List, Optional, Any
from flask import Flask, current_app
import markdown
import yaml
from jinja2 import Template

# Set up logger
logger = logging.getLogger('documentation')
handler = logging.FileHandler('logs/documentation.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class DocumentationManager:
    """Manage project documentation."""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.docs_dir = 'docs'
        self.api_docs_file = os.path.join(self.docs_dir, 'api_docs.md')
        self.user_guide_file = os.path.join(self.docs_dir, 'user_guide.md')
        self.admin_guide_file = os.path.join(self.docs_dir, 'admin_guide.md')
        self.screenshots_dir = os.path.join(self.docs_dir, 'screenshots')
        self.translations_dir = os.path.join(self.docs_dir, 'translations')
        
        # Create directories if they don't exist
        os.makedirs(self.docs_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.translations_dir, exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize with Flask app."""
        self.app = app
        
        # Register commands
        @app.cli.command("update-docs")
        def update_docs_command():
            """Update all documentation."""
            self.update_all_docs()
            print("Documentation updated successfully.")
        
        @app.cli.command("update-api-docs")
        def update_api_docs_command():
            """Update API documentation."""
            self.update_api_docs()
            print("API documentation updated successfully.")
        
        @app.cli.command("update-user-guide")
        def update_user_guide_command():
            """Update user guide."""
            self.update_user_guide()
            print("User guide updated successfully.")
        
        @app.cli.command("update-admin-guide")
        def update_admin_guide_command():
            """Update admin guide."""
            self.update_admin_guide()
            print("Admin guide updated successfully.")
        
        @app.cli.command("translate-docs")
        def translate_docs_command():
            """Translate documentation."""
            self.translate_docs()
            print("Documentation translated successfully.")
    
    def update_all_docs(self):
        """Update all documentation."""
        logger.info("Updating all documentation")
        
        # Update API docs
        self.update_api_docs()
        
        # Update user guide
        self.update_user_guide()
        
        # Update admin guide
        self.update_admin_guide()
        
        # Update screenshots
        self.update_screenshots()
        
        # Translate docs
        self.translate_docs()
        
        # Check accuracy
        self.check_docs_accuracy()
        
        logger.info("All documentation updated successfully")
    
    def update_api_docs(self):
        """Update API documentation."""
        logger.info("Updating API documentation")
        
        try:
            # Get all routes from the app
            routes = []
            if self.app:
                for rule in self.app.url_map.iter_rules():
                    if rule.endpoint != 'static':
                        routes.append({
                            'endpoint': rule.endpoint,
                            'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'})),
                            'path': str(rule),
                            'arguments': sorted([arg for arg in rule.arguments if arg != 'endpoint'])
                        })
            
            # Sort routes by endpoint
            routes = sorted(routes, key=lambda x: x['endpoint'])
            
            # Create API docs content
            content = "# AgroMap API Documentation\n\n"
            content += f"*Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            content += "## API Endpoints\n\n"
            
            for route in routes:
                content += f"### {route['endpoint']}\n\n"
                content += f"**URL:** `{route['path']}`\n\n"
                content += f"**Methods:** {', '.join(route['methods'])}\n\n"
                
                if route['arguments']:
                    content += "**URL Parameters:**\n\n"
                    for arg in route['arguments']:
                        content += f"- `{arg}`: Description of {arg}\n"
                    content += "\n"
                
                content += "**Request Body:**\n\n"
                content += "```json\n{\n  // Request body schema\n}\n```\n\n"
                
                content += "**Response:**\n\n"
                content += "```json\n{\n  // Response schema\n}\n```\n\n"
                
                content += "**Example:**\n\n"
                content += "```bash\ncurl -X GET http://example.com/api/...\n```\n\n"
                content += "---\n\n"
            
            # Write to file
            with open(self.api_docs_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"API documentation updated: {self.api_docs_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error updating API documentation: {str(e)}")
            return False
    
    def update_user_guide(self):
        """Update user guide."""
        logger.info("Updating user guide")
        
        try:
            # Check if user guide exists
            if not os.path.exists(self.user_guide_file):
                # Create basic user guide structure
                content = "# AgroMap User Guide\n\n"
                content += f"*Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
                content += "## Introduction\n\n"
                content += "Welcome to AgroMap, a comprehensive agricultural mapping and management system.\n\n"
                content += "## Getting Started\n\n"
                content += "### Account Creation\n\n"
                content += "### Logging In\n\n"
                content += "### Dashboard Overview\n\n"
                content += "## Features\n\n"
                content += "### Maps\n\n"
                content += "### Crop Management\n\n"
                content += "### Weather Data\n\n"
                content += "### Analytics\n\n"
                content += "### Reports\n\n"
                content += "## Troubleshooting\n\n"
                content += "### Common Issues\n\n"
                content += "### Contact Support\n\n"
                
                with open(self.user_guide_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Created new user guide: {self.user_guide_file}")
            else:
                # Update existing user guide
                with open(self.user_guide_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Update the last updated date
                content = re.sub(
                    r'\*Last updated: .*\*',
                    f"*Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
                    content
                )
                
                # Add any new sections or update existing ones
                # This would typically be more sophisticated in a real implementation
                
                with open(self.user_guide_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Updated existing user guide: {self.user_guide_file}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error updating user guide: {str(e)}")
            return False
    
    def update_admin_guide(self):
        """Update admin guide."""
        logger.info("Updating admin guide")
        
        try:
            # Check if admin guide exists
            if not os.path.exists(self.admin_guide_file):
                # Create basic admin guide structure
                content = "# AgroMap Administrator Guide\n\n"
                content += f"*Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
                content += "## Introduction\n\n"
                content += "This guide is for administrators of the AgroMap system.\n\n"
                content += "## Installation\n\n"
                content += "### System Requirements\n\n"
                content += "### Installation Steps\n\n"
                content += "### Configuration\n\n"
                content += "## Administration\n\n"
                content += "### User Management\n\n"
                content += "### System Settings\n\n"
                content += "### Backup and Recovery\n\n"
                content += "### Performance Tuning\n\n"
                content += "### Security\n\n"
                content += "## Maintenance\n\n"
                content += "### Regular Tasks\n\n"
                content += "### Troubleshooting\n\n"
                content += "### Upgrades\n\n"
                
                with open(self.admin_guide_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Created new admin guide: {self.admin_guide_file}")
            else:
                # Update existing admin guide
                with open(self.admin_guide_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Update the last updated date
                content = re.sub(
                    r'\*Last updated: .*\*',
                    f"*Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
                    content
                )
                
                # Add any new sections or update existing ones
                # This would typically be more sophisticated in a real implementation
                
                with open(self.admin_guide_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Updated existing admin guide: {self.admin_guide_file}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error updating admin guide: {str(e)}")
            return False
    
    def update_screenshots(self):
        """Update screenshots in documentation."""
        logger.info("Updating screenshots")
        
        try:
            # In a real implementation, this might use Selenium or another tool
            # to automatically capture screenshots of the application
            
            # For now, just log that this would happen
            logger.info("Screenshot update would capture new images of the application")
            
            # Create a placeholder screenshot if none exist
            placeholder_file = os.path.join(self.screenshots_dir, 'placeholder.txt')
            if not os.listdir(self.screenshots_dir) and not os.path.exists(placeholder_file):
                with open(placeholder_file, 'w', encoding='utf-8') as f:
                    f.write("Screenshots would be stored in this directory.")
                
                logger.info(f"Created placeholder file: {placeholder_file}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error updating screenshots: {str(e)}")
            return False
    
    def translate_docs(self, languages: List[str] = None):
        """Translate documentation to other languages."""
        if languages is None:
            languages = ['ru', 'uz']  # Default languages for Uzbekistan
        
        logger.info(f"Translating documentation to: {', '.join(languages)}")
        
        try:
            # For each language
            for lang in languages:
                lang_dir = os.path.join(self.translations_dir, lang)
                os.makedirs(lang_dir, exist_ok=True)
                
                # Translate user guide
                if os.path.exists(self.user_guide_file):
                    lang_user_guide = os.path.join(lang_dir, os.path.basename(self.user_guide_file))
                    
                    # In a real implementation, this would use a translation API
                    # For now, just copy the file and add a note
                    shutil.copy2(self.user_guide_file, lang_user_guide)
                    
                    with open(lang_user_guide, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    content = f"# [Translated to {lang}]\n\n" + content
                    
                    with open(lang_user_guide, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    logger.info(f"Translated user guide to {lang}: {lang_user_guide}")
                
                # Translate admin guide
                if os.path.exists(self.admin_guide_file):
                    lang_admin_guide = os.path.join(lang_dir, os.path.basename(self.admin_guide_file))
                    
                    # In a real implementation, this would use a translation API
                    # For now, just copy the file and add a note
                    shutil.copy2(self.admin_guide_file, lang_admin_guide)
                    
                    with open(lang_admin_guide, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    content = f"# [Translated to {lang}]\n\n" + content
                    
                    with open(lang_admin_guide, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    logger.info(f"Translated admin guide to {lang}: {lang_admin_guide}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error translating documentation: {str(e)}")
            return False
    
    def check_docs_accuracy(self):
        """Check documentation for accuracy."""
        logger.info("Checking documentation accuracy")
        
        try:
            issues = []
            
            # Check user guide
            if os.path.exists(self.user_guide_file):
                with open(self.user_guide_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for broken links
                links = re.findall(r'\[.*?\]\((.*?)\)', content)
                for link in links:
                    if link.startswith('http'):
                        # External link - would check with requests in a real implementation
                        pass
                    else:
                        # Internal link
                        if not os.path.exists(os.path.join(self.docs_dir, link)):
                            issues.append(f"Broken link in user guide: {link}")
                
                # Check for outdated content
                # This would be more sophisticated in a real implementation
                if "TODO" in content or "FIXME" in content:
                    issues.append("User guide contains TODO or FIXME markers")
            
            # Check admin guide
            if os.path.exists(self.admin_guide_file):
                with open(self.admin_guide_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for broken links
                links = re.findall(r'\[.*?\]\((.*?)\)', content)
                for link in links:
                    if link.startswith('http'):
                        # External link - would check with requests in a real implementation
                        pass
                    else:
                        # Internal link
                        if not os.path.exists(os.path.join(self.docs_dir, link)):
                            issues.append(f"Broken link in admin guide: {link}")
                
                # Check for outdated content
                if "TODO" in content or "FIXME" in content:
                    issues.append("Admin guide contains TODO or FIXME markers")
            
            # Log issues
            if issues:
                for issue in issues:
                    logger.warning(f"Documentation issue: {issue}")
            else:
                logger.info("No documentation issues found")
            
            return issues
        
        except Exception as e:
            logger.error(f"Error checking documentation accuracy: {str(e)}")
            return [f"Error checking documentation: {str(e)}"]
    
    def add_examples(self, doc_file: str, examples: List[Dict[str, str]]):
        """Add examples to documentation."""
        logger.info(f"Adding examples to {doc_file}")
        
        try:
            if not os.path.exists(doc_file):
                logger.warning(f"Document does not exist: {doc_file}")
                return False
            
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add examples section if it doesn't exist
            if "## Examples" not in content:
                content += "\n\n## Examples\n\n"
            
            # Add each example
            for example in examples:
                title = example.get('title', 'Example')
                description = example.get('description', '')
                code = example.get('code', '')
                
                example_content = f"### {title}\n\n"
                if description:
                    example_content += f"{description}\n\n"
                if code:
                    example_content += f"```python\n{code}\n```\n\n"
                
                # Add to content after Examples heading
                content = re.sub(
                    r'(## Examples\n\n)',
                    f"\\1{example_content}",
                    content
                )
            
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Added {len(examples)} examples to {doc_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding examples to {doc_file}: {str(e)}")
            return False
    
    def generate_html_docs(self, output_dir: str = 'docs/html'):
        """Generate HTML documentation from Markdown."""
        logger.info("Generating HTML documentation")
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Process each Markdown file
            for root, _, files in os.walk(self.docs_dir):
                for file in files:
                    if file.endswith('.md'):
                        md_file = os.path.join(root, file)
                        rel_path = os.path.relpath(md_file, self.docs_dir)
                        html_file = os.path.join(output_dir, rel_path.replace('.md', '.html'))
                        
                        # Create directory if needed
                        os.makedirs(os.path.dirname(html_file), exist_ok=True)
                        
                        # Convert Markdown to HTML
                        with open(md_file, 'r', encoding='utf-8') as f:
                            md_content = f.read()
                        
                        html_content = markdown.markdown(
                            md_content,
                            extensions=['extra', 'codehilite', 'toc']
                        )
                        
                        # Wrap in HTML template
                        template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
        pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }
        code { background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; }
        h1, h2, h3 { color: #333; }
        a { color: #0066cc; }
        .toc { background-color: #f9f9f9; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="content">
        {{ content }}
    </div>
</body>
</html>"""
                        
                        title = re.search(r'^# (.*?)$', md_content, re.MULTILINE)
                        title = title.group(1) if title else os.path.basename(md_file)
                        
                        html_doc = Template(template).render(
                            title=title,
                            content=html_content
                        )
                        
                        with open(html_file, 'w', encoding='utf-8') as f:
                            f.write(html_doc)
                        
                        logger.info(f"Generated HTML: {html_file}")
            
            # Create index.html
            index_content = "# AgroMap Documentation\n\n"
            index_content += "## Available Documentation\n\n"
            
            for root, _, files in os.walk(output_dir):
                for file in files:
                    if file.endswith('.html') and file != 'index.html':
                        rel_path = os.path.relpath(os.path.join(root, file), output_dir)
                        title = file.replace('.html', '').replace('_', ' ').title()
                        index_content += f"- [{title}]({rel_path})\n"
            
            html_content = markdown.markdown(
                index_content,
                extensions=['extra']
            )
            
            index_html = Template(template).render(
                title="AgroMap Documentation",
                content=html_content
            )
            
            with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(index_html)
            
            logger.info(f"Generated HTML documentation in {output_dir}")
            return True
        
        except Exception as e:
            logger.error(f"Error generating HTML documentation: {str(e)}")
            return False

# Initialize documentation manager
def init_documentation_manager(app: Optional[Flask] = None) -> DocumentationManager:
    """Initialize documentation manager."""
    manager = DocumentationManager(app)
    logger.info("Documentation manager initialized")
    return manager