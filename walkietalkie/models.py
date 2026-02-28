from django.db import models
from django.conf import settings


class WalkieTalkieGroup(models.Model):
    """Walkie-talkie group (e.g. First, Second)."""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'walkietalkie_groups'
        ordering = ['name']

    def __str__(self):
        return self.name


class WalkieTalkieGroupMember(models.Model):
    """Membership of a user in a walkie-talkie group."""
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(
        WalkieTalkieGroup,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='walkietalkie_memberships'
    )
    joined_at = models.DateTimeField(auto_now_add=True, db_column='joined_at')

    class Meta:
        db_table = 'walkietalkie_group_members'
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'user'],
                name='walkietalkie_group_member_unique'
            )
        ]
        ordering = ['group', 'joined_at']

    def __str__(self):
        return f"{self.user} in {self.group}"


class WalkieTalkieRecording(models.Model):
    """Metadata for a single PTT recording (audio file stored by Node)."""
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(
        WalkieTalkieGroup,
        on_delete=models.CASCADE,
        related_name='recordings'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='walkietalkie_recordings'
    )
    started_at = models.DateTimeField(db_column='started_at')
    ended_at = models.DateTimeField(db_column='ended_at')
    file_path = models.CharField(max_length=1024, blank=True, null=True)
    storage_key = models.CharField(max_length=1024, blank=True, null=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    sample_rate = models.IntegerField(null=True, blank=True, default=16000)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'walkietalkie_recordings'
        ordering = ['-started_at']

    def __str__(self):
        return f"Recording by {self.user} in {self.group} at {self.started_at}"
