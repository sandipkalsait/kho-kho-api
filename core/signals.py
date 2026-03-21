import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Tournament, Team, Player, Match, Inning, ScoreEvent

logger = logging.getLogger("core")

@receiver(post_save, sender=Tournament)
@receiver(post_save, sender=Team)
@receiver(post_save, sender=Player)
@receiver(post_save, sender=Match)
@receiver(post_save, sender=Inning)
def log_model_save(sender, instance, created, **kwargs):
    action = "Created" if created else "Updated"
    logger.info("%s: %s | ID: %s | Details: %s", 
                action, sender.__name__, instance.pk, str(instance))

@receiver(post_delete, sender=Tournament)
@receiver(post_delete, sender=Team)
@receiver(post_delete, sender=Player)
@receiver(post_delete, sender=Match)
@receiver(post_delete, sender=Inning)
def log_model_delete(sender, instance, **kwargs):
    logger.info("Deleted: %s | ID: %s | Details: %s", 
                sender.__name__, instance.pk, str(instance))
