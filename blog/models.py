import datetime
from django.db import models
from django.template.defaultfilters import slugify
from django.conf import settings
from core.models import *


class Category(StampedModel):
    title = models.CharField(max_length=64)    
    slug = models.SlugField(max_length=64, default="")
    description = models.TextField(max_length=512, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super(Category, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return ('view_category', None, {'slug': self.slug })

    class Meta:
        verbose_name_plural = "categories"
     
     
class Tag(models.Model):
    title = models.CharField(max_length=64)    
    slug = models.SlugField(max_length=64, default="")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.id:
            self.slug = slugify(self.title)
        super(Tag, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return ('view_tag', None, {'slug': self.slug })   


class Settings(StampedModel):
    title = models.CharField(max_length=128, default="", null=True, blank=True,)
    author = models.CharField(max_length=64, default="", null=True, blank=True,)    
    about = models.TextField(default="", null=True, blank=True, verbose_name="About page (markdown)")

    # Description for google search results
    description = models.TextField(max_length=512, blank=True, verbose_name="Google results description (ideally under 160 characters)")
    keywords = models.TextField(max_length=512, blank=True)

    # For facebook/twitter:
    description_social = models.TextField(max_length=512, blank=True)
    image_social = models.ImageField(upload_to = 'img/', default = '/media/img/social-card.png')

    # Analytics tracking number
    analytics = models.CharField(max_length=64, default="", null=True, blank=True,  verbose_name="Google Analytics tracking nuber (UA-XXXXXXXX).")    

    
    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "settings"
    


# Generate unique slug
def unique_slug(title):
    uniqueid = uuid.uuid1().hex[:5]                
    slug = slugify(title) + "-" + str(uniqueid)

    if not Post.objects.filter(slug=slug).exists():
        # If there's no posts with such slug,
        # then the slug is unique, so I return it
        return slug
    else:
        # If the post with this slug already exists -
        # I try to generate unique slug again
        return unique_slug(title)

    
class Post(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=256, default="")
    pub_date = models.DateTimeField(blank=True, null=True)
    body = models.TextField(default="", null=True, blank=True)
    published = models.BooleanField(default=False, blank=True)
    
    category = models.ForeignKey(Category, related_name="posts", on_delete=models.SET_NULL, blank=True, null=True) 
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)
    score = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title

    def save(self, slug="", *args, **kwargs):
        if not self.id:
            self.pub_date = datetime.datetime.now()
            self.slug = unique_slug(self.title)

        return super(Post, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return ('post_detail', None, {'slug': self.slug })

    
    class Meta:
        ordering = ('-pub_date',)

