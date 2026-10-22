import django.core.validators
import django.db.models.deletion
import utils.models
from django.conf import settings
from django.db import migrations, models


def clear_cohorts(apps, schema_editor):
    """Cohorts are being reshaped (group-of-trainees + CourseRun) and existing
    rows aren't worth preserving. Deleting cohorts cascades to their lesson
    releases and completions, leaving the tables clean for the new schema."""
    Cohort = apps.get_model("elearning", "Cohort")
    Cohort.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('elearning', '0004_lesson_deleted_module_deleted'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(clear_cohorts, migrations.RunPython.noop),
        # Cohort becomes a named group of trainees.
        migrations.AddField(
            model_name='cohort',
            name='members',
            field=models.ManyToManyField(blank=True, related_name='cohorts', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RemoveField(model_name='cohort', name='course'),
        migrations.RemoveField(model_name='cohort', name='circle'),
        migrations.RemoveField(model_name='cohort', name='start_date'),
        migrations.RemoveField(model_name='cohort', name='send_hour'),
        migrations.RemoveField(model_name='cohort', name='active'),
        # CourseRun owns the drip schedule (course + start_date + send_hour).
        migrations.CreateModel(
            name='CourseRun',
            fields=[
                ('id', models.CharField(default=utils.models.generate_ulid, editable=False, max_length=26, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('start_date', models.DateField()),
                ('send_hour', models.PositiveSmallIntegerField(default=14, help_text='Hour of day (0-23, Asia/Dili) at which due lessons are sent.', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(23)])),
                ('active', models.BooleanField(default=True)),
                ('cohort', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='elearning.cohort')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='elearning.course')),
            ],
            options={
                'db_table': 'elearning_course_runs',
                'ordering': ['-created'],
            },
        ),
        # LessonRelease now hangs off the run, not the cohort.
        migrations.AlterUniqueTogether(
            name='lessonrelease',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='lessonrelease',
            name='cohort',
        ),
        migrations.AddField(
            model_name='lessonrelease',
            name='run',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='releases', to='elearning.courserun'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='lessonrelease',
            unique_together={('run', 'lesson')},
        ),
    ]
