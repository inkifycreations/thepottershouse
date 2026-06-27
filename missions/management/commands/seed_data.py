from django.core.management.base import BaseCommand
from missions.models import State, Pastor

class Command(BaseCommand):
    help = 'Seeds the database with India states, initial pastors, and referral codes.'

    def handle(self, *args, **options):
        # 1. State data list
        states_data = [
            # RED States (Not Reached)
            {'code': 'ar', 'name': 'Arunachal Pradesh', 'population': '1.4 Million', 'status': 'RED', 'description': 'Deep valleys and mountainous terrain. Very few local fellowship works established.'},
            {'code': 'as', 'name': 'Assam', 'population': '31.2 Million', 'status': 'RED', 'description': 'The gateway to the North-East. Large tea garden populations with immense spiritual needs.'},
            {'code': 'br', 'name': 'Bihar', 'population': '103.8 Million', 'status': 'RED', 'description': 'One of the least reached states. Over 100 million souls waiting for the message of hope.'},
            {'code': 'ct', 'name': 'Chhattisgarh', 'population': '25.5 Million', 'status': 'RED', 'description': 'Tribal heartlands. Great opportunities for pioneering works.'},
            {'code': 'gj', 'name': 'Gujarat', 'population': '60.4 Million', 'status': 'RED', 'description': 'Rapidly growing urban centers. Strong need for church planting.'},
            {'code': 'hr', 'name': 'Haryana', 'population': '25.4 Million', 'status': 'RED', 'description': 'Surrounding the capital. High demand for outreach in developing cities.'},
            {'code': 'hp', 'name': 'Himachal Pradesh', 'population': '6.9 Million', 'status': 'RED', 'description': 'Mountain communities where many have never heard the gospel.'},
            {'code': 'jh', 'name': 'Jharkhand', 'population': '33.0 Million', 'status': 'RED', 'description': 'Mineral-rich lands. Large tribal population ready for discipleship.'},
            {'code': 'mp', 'name': 'Madhya Pradesh', 'population': '72.6 Million', 'status': 'RED', 'description': 'Central India. Pockets of revival exist but the harvest field is massive.'},
            {'code': 'mn', 'name': 'Manipur', 'population': '2.7 Million', 'status': 'RED', 'description': 'Challenging terrain with localized communities needing prayer.'},
            {'code': 'ml', 'name': 'Meghalaya', 'population': '3.0 Million', 'status': 'RED', 'description': 'Hills and rain-swept regions. Opportunities for training leaders.'},
            {'code': 'mz', 'name': 'Mizoram', 'population': '1.1 Million', 'status': 'RED', 'description': 'High literacy. Need for sending and missionary support.'},
            {'code': 'nl', 'name': 'Nagaland', 'population': '2.0 Million', 'status': 'RED', 'description': 'Rich culture. Ideal launching pad for missions.'},
            {'code': 'or', 'name': 'Odisha', 'population': '41.9 Million', 'status': 'RED', 'description': 'Coastal and tribal areas. Urgent need for Bible study groups.'},
            {'code': 'pb', 'name': 'Punjab', 'population': '27.7 Million', 'status': 'RED', 'description': 'Vibrant communities. Growing openness to house church networks.'},
            {'code': 'rj', 'name': 'Rajasthan', 'population': '68.6 Million', 'status': 'RED', 'description': 'Desert regions and historic cities. Massive unreached areas.'},
            {'code': 'sk', 'name': 'Sikkim', 'population': '0.6 Million', 'status': 'RED', 'description': 'Himalayan state. Small, scattered populations needing fellowship.'},
            {'code': 'tr', 'name': 'Tripura', 'population': '3.7 Million', 'status': 'RED', 'description': 'Bordering regions. Ready fields for church planting.'},
            {'code': 'up', 'name': 'Uttar Pradesh', 'population': '199.8 Million', 'status': 'RED', 'description': 'Indias most populous state. A critical mission field with millions needing salvation.'},
            {'code': 'ut', 'name': 'Uttarakhand', 'population': '10.1 Million', 'status': 'RED', 'description': 'Devbhoomi (Land of Gods). High spiritual barriers requiring persistent prayer.'},

            # BLUE States (Reached, Work Remaining)
            {'code': 'ap', 'name': 'Andhra Pradesh', 'population': '49.4 Million', 'status': 'BLUE', 'description': 'Established churches exist, but rural and tribal regions require major reinforcement.'},
            {'code': 'dl', 'name': 'Delhi', 'population': '16.8 Million', 'status': 'BLUE', 'description': 'National Capital Territory. Active urban ministries with ongoing pioneer works in surrounding regions.'},
            {'code': 'ga', 'name': 'Goa', 'population': '1.5 Million', 'status': 'BLUE', 'description': 'Historical Christian presence, but deep spiritual renewal is needed among the youth.'},
            {'code': 'ka', 'name': 'Karnataka', 'population': '61.1 Million', 'status': 'BLUE', 'description': 'Metropolitan centers have congregations; northern districts are still largely unreached.'},
            {'code': 'kl', 'name': 'Kerala', 'population': '33.4 Million', 'status': 'BLUE', 'description': 'Strong traditional roots; requires fresh zeal and pioneering works for the current generation.'},
            {'code': 'mh', 'name': 'Maharashtra', 'population': '112.4 Million', 'status': 'BLUE', 'description': 'Huge urban slums and rural hinterlands with a high demand for discipleship.'},
            {'code': 'tn', 'name': 'Tamil Nadu', 'population': '72.1 Million', 'status': 'BLUE', 'description': 'Many active ministries, yet millions remain without personal knowledge of the gospel.'},
            {'code': 'tg', 'name': 'Telangana', 'population': '35.2 Million', 'status': 'BLUE', 'description': 'Established urban fellowships, but villages need persistent pioneer evangelism.'},
            {'code': 'wb', 'name': 'West Bengal', 'population': '91.3 Million', 'status': 'BLUE', 'description': 'Active works under local pastors, but rural districts need persistent pioneer planting.'},
        ]

        self.stdout.write('Seeding states...')
        for sd in states_data:
            state, created = State.objects.get_or_create(
                code=sd['code'],
                defaults={
                    'name': sd['name'],
                    'population': sd['population'],
                    'status': sd['status'],
                    'description': sd['description']
                }
            )
            if not created:
                # Update attributes if they exist
                state.name = sd['name']
                state.population = sd['population']
                state.status = sd['status']
                state.description = sd['description']
                state.save()

        self.stdout.write('Seeding pastors and referral codes...')
        
        # West Bengal pastors
        wb_state = State.objects.get(code='wb')
        Pastor.objects.get_or_create(name='Chris', state=wb_state, referral_code='CHRIS_WB')
        Pastor.objects.get_or_create(name='Stephen', state=wb_state, referral_code='STEPHEN_WB')

        # Create at least one pastor for each of the other states to make testing easy
        pastor_names = {
            'ap': 'Rajesh', 'ar': 'Tashi', 'as': 'Barua', 'br': 'Manoj', 'ct': 'Sanjay',
            'dl': 'Gurmeet', 'ga': 'Francis', 'gj': 'Kirit', 'hr': 'Vikram', 'hp': 'Prem', 'jh': 'Anil',
            'ka': 'Joseph', 'kl': 'Thomas', 'mp': 'David', 'mh': 'Daniel', 'mn': 'Ibobi',
            'ml': 'Sangma', 'mz': 'Laltha', 'nl': 'Ao', 'or': 'Das', 'pb': 'Harpreet',
            'rj': 'Shekhawat', 'sk': 'Bhutia', 'tn': 'Paul', 'tg': 'Srinivas', 'tr': 'Debbarma',
            'up': 'Amit', 'ut': 'Negi'
        }

        for code, name in pastor_names.items():
            try:
                state_obj = State.objects.get(code=code)
                Pastor.objects.get_or_create(
                    name=name,
                    state=state_obj,
                    referral_code=f"{name.upper()}_{code.upper()}"
                )
            except State.DoesNotExist:
                pass

        self.stdout.write(self.style.SUCCESS('Successfully seeded database!'))
