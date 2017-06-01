import factory
from accounts.models import User
from accounts.models import Reviewer


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('first_name')
    email = factory.LazyAttribute(lambda a: '{0}.{1}@example.com'.format(a.first_name, a.last_name).lower())
    is_active = True


class ReviewerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reviewer
