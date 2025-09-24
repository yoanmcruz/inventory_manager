from django.core.management.base import BaseCommand
from django.urls import get_resolver

class Command(BaseCommand):
    help = 'List all URLs defined in the project'
    
    def handle(self, *args, **options):
        resolver = get_resolver()
        patterns = resolver.url_patterns
        
        self.stdout.write("URLs definidas en el proyecto:")
        self.stdout.write("=" * 50)
        
        self.list_patterns(patterns)
    
    def list_patterns(self, patterns, prefix=''):
        for pattern in patterns:
            if hasattr(pattern, 'url_patterns'):
                # Es un include
                self.list_patterns(pattern.url_patterns, prefix + str(pattern.pattern))
            else:
                # Es un path normal
                self.stdout.write(f"{prefix + str(pattern.pattern):40} {pattern.name or '[no name]'}")