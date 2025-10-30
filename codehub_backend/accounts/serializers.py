from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Skill, CareerInterest, Badge


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for Skill model"""

    class Meta:
        model = Skill
        fields = ['id', 'name', 'category', 'description', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CareerInterestSerializer(serializers.ModelSerializer):
    """Serializer for CareerInterest model"""

    class Meta:
        model = CareerInterest
        fields = ['id', 'name', 'description', 'industry', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class BadgeSerializer(serializers.ModelSerializer):
    """Serializer for Badge model"""

    class Meta:
        model = Badge
        fields = [
            'id', 'name', 'description', 'icon', 'badge_type',
            'points_required', 'criteria', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile information"""
    skills = SkillSerializer(many=True, read_only=True)
    career_interests = CareerInterestSerializer(many=True, read_only=True)
    badges = BadgeSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role',
            'program', 'year_level', 'student_id', 'bio', 'avatar',
            'github_username', 'linkedin_url', 'portfolio_url',
            'skills', 'career_interests', 'badges', 'points', 'level',
            'is_verified', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'points', 'level', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'program', 'year_level',
            'student_id', 'bio'
        ]

    def validate(self, attrs):
        """Validate password confirmation matches"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Password confirmation does not match.'
            })
        return attrs

    def create(self, validated_data):
        """Create new user with encrypted password"""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information"""
    current_password = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'bio', 'avatar',
            'github_username', 'linkedin_url', 'portfolio_url',
            'current_password', 'new_password'
        ]

    def validate(self, attrs):
        """Validate password change if requested"""
        user = self.instance
        current_password = attrs.get('current_password')
        new_password = attrs.get('new_password')

        if new_password and not current_password:
            raise serializers.ValidationError({
                'current_password': 'Current password is required to set new password.'
            })

        if current_password and new_password:
            if not user.check_password(current_password):
                raise serializers.ValidationError({
                    'current_password': 'Current password is incorrect.'
                })

        return attrs

    def update(self, instance, validated_data):
        """Update user instance"""
        current_password = validated_data.pop('current_password', None)
        new_password = validated_data.pop('new_password', None)

        # Update password if provided
        if new_password:
            instance.set_password(new_password)

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate user credentials"""
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Authenticate user
            user = authenticate(username=email, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError({
                        'email': 'User account is disabled.'
                    })
                attrs['user'] = user
                return attrs
            else:
                raise serializers.ValidationError({
                    'email': 'Unable to log in with provided credentials.'
                })
        else:
            raise serializers.ValidationError({
                'email': 'Email and password are required.'
            })


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Validate email exists"""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError({
                'email': 'No user found with this email address.'
            })
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    token = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate password confirmation matches"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Password confirmation does not match.'
            })
        return attrs


class FollowUserSerializer(serializers.Serializer):
    """Serializer for following/unfollowing users"""
    user_id = serializers.UUIDField(required=True)

    def validate_user_id(self, value):
        """Validate user exists and is not trying to follow themselves"""
        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'user_id': 'User not found.'
            })

        request_user = self.context['request'].user
        if user == request_user:
            raise serializers.ValidationError({
                'user_id': 'Cannot follow yourself.'
            })

        return value


class UserStatsSerializer(serializers.ModelSerializer):
    """Serializer for user statistics"""
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    projects_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'points', 'level', 'followers_count',
            'following_count', 'posts_count', 'projects_count'
        ]
        read_only_fields = fields

    def get_followers_count(self, obj):
        """Get followers count"""
        return obj.get_followers_count()

    def get_following_count(self, obj):
        """Get following count"""
        return obj.get_following_count()

    def get_posts_count(self, obj):
        """Get posts count"""
        return obj.posts.count()

    def get_projects_count(self, obj):
        """Get projects count"""
        return obj.owned_projects.count()