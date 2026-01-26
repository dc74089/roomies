from django.core.management.base import BaseCommand
from datetime import datetime
from app.utils.all import run_in_parallel
from app.models import Solution


class Command(BaseCommand):
    help = 'Generate room assignments using all algorithms in parallel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--gender',
            type=str,
            choices=['male', 'female'],
            help='Generate solutions for specific gender only (default: both)',
        )
        parser.add_argument(
            '--depth',
            type=int,
            default=1000,
            help='Number of iterations per algorithm (default: 1000)',
        )

    def handle(self, *args, **options):
        gender = options.get('gender')
        depth = options.get('depth')

        self.stdout.write('='*70)
        self.stdout.write(self.style.SUCCESS('ROOM GENERATION - PARALLEL EXECUTION'))
        self.stdout.write('='*70)
        self.stdout.write(f'Started at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        self.stdout.write('')

        # Configuration
        self.stdout.write('Configuration:')
        self.stdout.write(f'  Gender: {gender if gender else "Both (Male and Female)"}')
        self.stdout.write(f'  Iterations: {depth}')
        self.stdout.write('')

        # Show algorithms
        self.stdout.write('Algorithms running in parallel:')
        self.stdout.write('  - Simulated Annealing (best performer)')
        self.stdout.write('  - Greedy Smart (cached greedy with affinity)')
        self.stdout.write('  - Sum (round-robin placement)')
        self.stdout.write('')

        self.stdout.write('='*70)
        self.stdout.write('RUNNING... (this may take 10-30 minutes)')
        self.stdout.write('='*70)
        self.stdout.write('')

        try:
            start_time = datetime.now()

            # Run algorithms in parallel
            futures, tune_futures = run_in_parallel(gender=gender, depth=depth)

            end_time = datetime.now()
            duration = end_time - start_time

            self.stdout.write('')
            self.stdout.write('='*70)
            self.stdout.write(self.style.SUCCESS('COMPLETED'))
            self.stdout.write('='*70)
            self.stdout.write(f'Duration: {duration}')
            self.stdout.write('')

            # Show results
            self.stdout.write('Results by Strategy:')
            self.stdout.write('-'*70)

            strategies = ['Simulated Annealing', 'Improved Greedy Room', 'Sum']
            for strategy in strategies:
                solns = Solution.objects.filter(strategy=strategy).order_by('-id')[:2]
                if solns.exists():
                    self.stdout.write(f'\n{strategy}:')
                    for soln in solns:
                        status = '✓' if soln.score < 10000 else '✗'
                        self.stdout.write(
                            f'  {status} {soln.name} (ID: {soln.id}) - Score: {soln.score:.2f}'
                        )

            self.stdout.write('')
            self.stdout.write('='*70)
            self.stdout.write(self.style.SUCCESS('View solutions in the Django admin panel'))
            self.stdout.write('='*70)

        except KeyboardInterrupt:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Interrupted by user'))
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            import traceback
            traceback.print_exc()
