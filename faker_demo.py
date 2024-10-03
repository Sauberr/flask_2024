from faker import Faker

faker = Faker('UK')


# print(faker.first_name())
# print(faker.last_name())


for customer in range(10_000):
    print(faker.profile())