from rest_framework import serializers

from blog.models import *


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('title', 'slug', 'description')


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = '__all__'


class TagSlugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('title', 'slug')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('title', 'slug')
        

class PostSerializer(serializers.ModelSerializer):
    # Include the whole tag object into the post(use for comments):
    tags = TagSlugSerializer(read_only=True, many=True)
    # Include just the tag's slugs:
    # tags = serializers.SlugRelatedField(
    #     many=True,
    #     read_only=True,
    #     slug_field='slug')    

    category = CategorySerializer(read_only=True)
    
    class Meta:
        model = Post
        fields = ('title', 'slug', 'published', 'body', 'category', 'tags')

        lookup_field = 'slug'

        

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('title', 'slug')
