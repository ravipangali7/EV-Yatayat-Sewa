from django.db import models


class Slider(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=500, blank=True, default='')
    image = models.ImageField(upload_to='uploads/website/sliders/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'website_sliders'
        indexes = [models.Index(fields=['is_active'])]

    def __str__(self):
        return self.title


class CMSPage(models.Model):
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    image = models.ImageField(upload_to='uploads/website/cms/', blank=True, null=True)
    content = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    is_footer = models.BooleanField(default=False)
    is_header = models.BooleanField(default=False)
    is_about = models.BooleanField(default=False)
    section_in = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_sections'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'website_cms_pages'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_about']),
            models.Index(fields=['is_active', 'is_header']),
            models.Index(fields=['section_in']),
        ]

    def __str__(self):
        return f"{self.title} ({self.slug})"


class Team(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.IntegerField(default=0)
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='uploads/website/team/', blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    address = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'website_team'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return self.name


class Testimonial(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    message = models.TextField()
    star = models.IntegerField(default=5)
    image = models.ImageField(upload_to='uploads/website/testimonials/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'website_testimonials'
        indexes = [models.Index(fields=['is_active'])]

    def __str__(self):
        return self.name


class Service(models.Model):
    """Website service (e.g. City Transport, Charter). Design uses title/desc/icon."""
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    svg = models.TextField(blank=True, default='')
    description = models.TextField(blank=True, default='')
    # Lucide icon name for new design (e.g. Bus, Building2, Mountain, CalendarCheck, Plane, GraduationCap)
    icon = models.CharField(max_length=50, blank=True, default='')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'website_services'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return self.name


class FAQ(models.Model):
    id = models.BigAutoField(primary_key=True)
    question = models.CharField(max_length=500)
    answer = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'website_faqs'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return self.question[:80]


class ContactMessage(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'website_contact_messages'

    def __str__(self):
        return f"{self.name} - {self.created_at}"


class Blog(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    image = models.ImageField(upload_to='uploads/website/blog/', blank=True, null=True)
    content = models.TextField(blank=True, default='')
    # Short summary for cards/list; design uses excerpt
    excerpt = models.CharField(max_length=500, blank=True, default='')
    # Category label for design (e.g. Industry, Travel, Education, News)
    category = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'website_blogs'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class SiteSetting(models.Model):
    id = models.BigAutoField(primary_key=True)
    logo = models.ImageField(upload_to='uploads/website/site/', blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, default='')
    tagline = models.CharField(max_length=500, blank=True, default='')
    phones = models.JSONField(default=list, blank=True)  # ["+977...", ...]
    emails = models.JSONField(default=list, blank=True)  # ["a@b.com", ...]
    address = models.TextField(blank=True, default='')
    map = models.TextField(blank=True, default='')  # URL or embed
    cover_image = models.ImageField(upload_to='uploads/website/site/', blank=True, null=True)
    footer_text = models.TextField(blank=True, default='')
    stats = models.JSONField(default=dict, blank=True)  # {"stats": [{"label","svg","value"}, ...]}
    about_image = models.ImageField(upload_to='uploads/website/site/', blank=True, null=True)
    about_title = models.CharField(max_length=500, blank=True, default='')
    about_content = models.TextField(blank=True, default='')  # HTML from CKEditor
    mission = models.TextField(blank=True, default='')
    vision = models.TextField(blank=True, default='')
    values = models.TextField(blank=True, default='')  # plain text, shown like mission/vision
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    class Meta:
        db_table = 'website_site_settings'

    def __str__(self):
        return self.name or f"Site Setting #{self.id}"
