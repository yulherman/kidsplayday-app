"""
Seed data for Camp-at-Home themed weeks.
Run once to populate the themed_weeks table.
"""

THEMED_WEEKS_DATA = [
    {
        "title_uk": "Тиждень науки",
        "title_en": "Science Week",
        "description_uk": "5 днів захопливих експериментів вдома. Від хімії до астрономії!",
        "description_en": "5 days of exciting experiments at home. From chemistry to astronomy!",
        "target_age_min": 48,
        "target_age_max": 144,
        "materials_shopping_list": [
            "baking soda", "vinegar", "food coloring", "oil", "empty bottles",
            "balloons", "magnifying glass", "paper", "tape", "seeds", "soil", "small pot",
        ],
        "day_plans": {
            "monday": {
                "theme_uk": "Хімія вдома",
                "theme_en": "Kitchen Chemistry",
                "activities": [
                    {
                        "title_uk": "Вулкан з соди та оцту",
                        "title_en": "Baking soda volcano",
                        "duration_minutes": 30,
                        "description_en": "Build a volcano from a bottle, clay or sand, and watch it erupt with baking soda and vinegar. Add food coloring for lava effect. Requires adult supervision.",
                        "materials": ["baking soda", "vinegar", "food coloring", "empty bottle", "sand or clay"],
                    },
                    {
                        "title_uk": "Невидиме чорнило з лимону",
                        "title_en": "Invisible lemon ink",
                        "duration_minutes": 20,
                        "description_en": "Write secret messages with lemon juice on white paper. Hold near a lamp to reveal the hidden text. Requires adult supervision.",
                        "materials": ["lemon", "paper", "cotton swab", "lamp"],
                    },
                    {
                        "title_uk": "Лавова лампа в пляшці",
                        "title_en": "Lava lamp in a bottle",
                        "duration_minutes": 25,
                        "description_en": "Fill a bottle with water and oil, add food coloring and a fizzy tablet. Watch colorful blobs rise and fall. Requires adult supervision.",
                        "materials": ["empty bottle", "oil", "water", "food coloring", "fizzy tablet"],
                    },
                ],
            },
            "tuesday": {
                "theme_uk": "Фізика та механіка",
                "theme_en": "Physics & Engineering",
                "activities": [
                    {
                        "title_uk": "Катапульта з паличок від морозива",
                        "title_en": "Popsicle stick catapult",
                        "duration_minutes": 35,
                        "description_en": "Build a catapult from popsicle sticks, rubber bands, and a bottle cap. Launch mini marshmallows and measure distances. Requires adult supervision.",
                        "materials": ["popsicle sticks", "rubber bands", "bottle cap", "mini marshmallows"],
                    },
                    {
                        "title_uk": "Міст з паперу який тримає вагу",
                        "title_en": "Paper bridge challenge",
                        "duration_minutes": 30,
                        "description_en": "Using only paper and tape, build a bridge between two books that can hold the most coins. Test different folding techniques. Requires adult supervision.",
                        "materials": ["paper", "tape", "coins", "books"],
                    },
                ],
            },
            "wednesday": {
                "theme_uk": "Біологія та природа",
                "theme_en": "Biology & Nature",
                "activities": [
                    {
                        "title_uk": "Посади насіння та почни щоденник",
                        "title_en": "Plant seeds and start a journal",
                        "duration_minutes": 30,
                        "description_en": "Plant beans or sunflower seeds in a small pot. Start a daily observation journal with drawings and measurements. Requires adult supervision.",
                        "materials": ["seeds", "soil", "small pot", "paper", "crayons"],
                    },
                    {
                        "title_uk": "Дослідження комах з лупою",
                        "title_en": "Bug safari with magnifying glass",
                        "duration_minutes": 40,
                        "description_en": "Go outside with a magnifying glass and explore insects. Draw what you find and try to identify species. Requires adult supervision.",
                        "materials": ["magnifying glass", "paper", "crayons"],
                    },
                ],
            },
            "thursday": {
                "theme_uk": "Астрономія та космос",
                "theme_en": "Astronomy & Space",
                "activities": [
                    {
                        "title_uk": "Модель сонячної системи",
                        "title_en": "Solar system model",
                        "duration_minutes": 45,
                        "description_en": "Create a solar system model using balls of different sizes (fruit, play dough, paper balls). Label planets and learn their order. Requires adult supervision.",
                        "materials": ["play dough or fruit", "paper", "string", "markers"],
                    },
                    {
                        "title_uk": "Карта сузір'їв (для вечора)",
                        "title_en": "Star map (evening activity)",
                        "duration_minutes": 30,
                        "description_en": "Print or draw a simple star map. In the evening, go outside and try to find the Big Dipper and other constellations. Requires adult supervision.",
                        "materials": ["paper", "pencil", "flashlight"],
                    },
                ],
            },
            "friday": {
                "theme_uk": "Наукова ярмарка",
                "theme_en": "Science Fair Friday",
                "activities": [
                    {
                        "title_uk": "Підготуй свій найкращий експеримент",
                        "title_en": "Prepare your best experiment",
                        "duration_minutes": 40,
                        "description_en": "Choose the best experiment from this week, repeat it, and prepare a presentation poster. Practice explaining how it works. Requires adult supervision.",
                        "materials": ["paper", "markers", "materials from favorite experiment"],
                    },
                    {
                        "title_uk": "Покажи свою науку родині!",
                        "title_en": "Present your science to the family!",
                        "duration_minutes": 30,
                        "description_en": "Set up a 'science fair' at home. Present your experiment and poster to family members. Answer their questions like a real scientist! Requires adult supervision.",
                        "materials": ["poster from previous activity"],
                    },
                ],
            },
        },
    },
    {
        "title_uk": "Тиждень кулінарії",
        "title_en": "Cooking Week",
        "description_uk": "Навчись готувати прості та смачні страви! Від сніданку до десерту.",
        "description_en": "Learn to cook simple and delicious dishes! From breakfast to dessert.",
        "target_age_min": 60,
        "target_age_max": 144,
        "materials_shopping_list": [
            "flour", "sugar", "eggs", "butter", "milk", "fruits", "vegetables",
            "cheese", "bread", "honey", "oats", "chocolate chips", "vanilla",
        ],
        "day_plans": {
            "monday": {
                "theme_uk": "Сніданок шефа",
                "theme_en": "Chef's Breakfast",
                "activities": [
                    {
                        "title_uk": "Панкейки з фруктовим обличчям",
                        "title_en": "Pancakes with fruit faces",
                        "duration_minutes": 40,
                        "description_en": "Make simple pancakes and decorate them with fruit slices to create funny faces. Learn to measure ingredients and mix batter. Requires adult supervision.",
                        "materials": ["flour", "eggs", "milk", "fruits", "butter"],
                    },
                    {
                        "title_uk": "Смузі-бар: створи свій рецепт",
                        "title_en": "Smoothie bar: create your recipe",
                        "duration_minutes": 20,
                        "description_en": "Set out various fruits, yogurt, honey, and oats. Create your own smoothie recipe, name it, and rate it. Write down the recipe card. Requires adult supervision.",
                        "materials": ["fruits", "yogurt", "honey", "oats", "blender"],
                    },
                ],
            },
            "tuesday": {
                "theme_uk": "Обід навколо світу",
                "theme_en": "Lunch Around the World",
                "activities": [
                    {
                        "title_uk": "Міні-піци з різних країн",
                        "title_en": "Mini pizzas from different countries",
                        "duration_minutes": 50,
                        "description_en": "Make mini pizzas with different toppings inspired by countries: Italian (tomato+mozzarella), French (cheese+ham), Hawaiian (pineapple). Requires adult supervision.",
                        "materials": ["bread or tortillas", "cheese", "tomato sauce", "various toppings"],
                    },
                ],
            },
            "wednesday": {
                "theme_uk": "Випічка та десерти",
                "theme_en": "Baking & Desserts",
                "activities": [
                    {
                        "title_uk": "Печиво без випікання",
                        "title_en": "No-bake cookies",
                        "duration_minutes": 30,
                        "description_en": "Mix oats, honey, cocoa, and butter to make no-bake energy balls. Roll in coconut or sprinkles. Requires adult supervision.",
                        "materials": ["oats", "honey", "cocoa", "butter", "coconut flakes"],
                    },
                    {
                        "title_uk": "Декорування кексів",
                        "title_en": "Cupcake decorating challenge",
                        "duration_minutes": 40,
                        "description_en": "Bake simple cupcakes (or use store-bought), then have a decorating competition using frosting, sprinkles, and candy. Requires adult supervision.",
                        "materials": ["cupcakes", "frosting", "sprinkles", "candy"],
                    },
                ],
            },
            "thursday": {
                "theme_uk": "Здорове харчування",
                "theme_en": "Healthy Eating Day",
                "activities": [
                    {
                        "title_uk": "Салат-конструктор",
                        "title_en": "Build-your-own salad bar",
                        "duration_minutes": 25,
                        "description_en": "Set out bowls of different vegetables, proteins, and dressings. Each person builds their dream salad. Rate each other's creations. Requires adult supervision.",
                        "materials": ["lettuce", "tomatoes", "cucumbers", "corn", "cheese", "dressing"],
                    },
                    {
                        "title_uk": "Фруктовий шашлик на паличці",
                        "title_en": "Fruit kebabs on sticks",
                        "duration_minutes": 20,
                        "description_en": "Thread colorful fruit pieces onto wooden skewers to make rainbow fruit kebabs. Dip in yogurt or chocolate. Requires adult supervision.",
                        "materials": ["various fruits", "wooden skewers", "yogurt or chocolate"],
                    },
                ],
            },
            "friday": {
                "theme_uk": "Ресторан вдома",
                "theme_en": "Home Restaurant",
                "activities": [
                    {
                        "title_uk": "Створи меню та прикрась стіл",
                        "title_en": "Create a menu and decorate the table",
                        "duration_minutes": 30,
                        "description_en": "Design a restaurant menu with appetizer, main course, and dessert. Fold napkins, make place cards, and decorate the dining table. Requires adult supervision.",
                        "materials": ["paper", "markers", "napkins"],
                    },
                    {
                        "title_uk": "Приготуй вечерю для родини!",
                        "title_en": "Cook dinner for the family!",
                        "duration_minutes": 60,
                        "description_en": "Using recipes learned this week, prepare a simple dinner for the whole family. Serve it restaurant-style from your menu! Requires adult supervision.",
                        "materials": ["ingredients based on chosen menu"],
                    },
                ],
            },
        },
    },
    {
        "title_uk": "Тиждень мистецтва",
        "title_en": "Art Week",
        "description_uk": "Малюй, ліпи, створюй! Від живопису до скульптури.",
        "description_en": "Draw, sculpt, create! From painting to sculpture.",
        "target_age_min": 24,
        "target_age_max": 144,
        "materials_shopping_list": [
            "paint", "brushes", "paper (large)", "cardboard", "play dough",
            "crayons", "markers", "glue", "scissors (child-safe)", "fabric scraps",
            "string", "cotton balls", "newspaper",
        ],
        "day_plans": {
            "monday": {
                "theme_uk": "Живопис",
                "theme_en": "Painting Day",
                "activities": [
                    {
                        "title_uk": "Абстрактний живопис руками (малюки) / пензликом (старші)",
                        "title_en": "Abstract finger painting (toddlers) / brush painting (older)",
                        "duration_minutes": 30,
                        "description_en": "Cover the table with newspaper, put on old clothes, and create abstract art. Toddlers use fingers, older kids use brushes and experiment with color mixing. Requires adult supervision.",
                        "materials": ["paint", "paper", "brushes", "newspaper"],
                    },
                ],
            },
            "tuesday": {
                "theme_uk": "Скульптура",
                "theme_en": "Sculpture Day",
                "activities": [
                    {
                        "title_uk": "Ліпка тварин з пластиліну або тіста",
                        "title_en": "Sculpt animals from play dough",
                        "duration_minutes": 35,
                        "description_en": "Choose your favorite animal and sculpt it from play dough. Create an entire zoo or farm! Requires adult supervision.",
                        "materials": ["play dough", "toothpicks", "googly eyes (optional)"],
                    },
                ],
            },
            "wednesday": {
                "theme_uk": "Колаж та аплікація",
                "theme_en": "Collage Day",
                "activities": [
                    {
                        "title_uk": "Колаж 'Моя мрія' з журналів",
                        "title_en": "Dream collage from magazines",
                        "duration_minutes": 40,
                        "description_en": "Cut out pictures from old magazines and create a 'dream board' collage about what makes you happy or what you want to be. Requires adult supervision.",
                        "materials": ["old magazines", "scissors (child-safe)", "glue", "cardboard"],
                    },
                ],
            },
            "thursday": {
                "theme_uk": "Архітектура",
                "theme_en": "Architecture Day",
                "activities": [
                    {
                        "title_uk": "Побудуй місто з картону",
                        "title_en": "Build a cardboard city",
                        "duration_minutes": 50,
                        "description_en": "Use cardboard boxes, tubes, and tape to build houses, towers, and bridges. Paint and decorate your city. Add toy cars and figures. Requires adult supervision.",
                        "materials": ["cardboard", "tape", "scissors (child-safe)", "paint", "markers"],
                    },
                ],
            },
            "friday": {
                "theme_uk": "Виставка мистецтва",
                "theme_en": "Art Exhibition Friday",
                "activities": [
                    {
                        "title_uk": "Влаштуй виставку своїх робіт",
                        "title_en": "Host your art exhibition",
                        "duration_minutes": 40,
                        "description_en": "Hang all the art from this week on the walls. Write labels for each piece. Invite family for a gallery opening! Serve juice and crackers. Requires adult supervision.",
                        "materials": ["tape", "paper for labels", "all art from the week"],
                    },
                ],
            },
        },
    },
    {
        "title_uk": "Тиждень пригод на вулиці",
        "title_en": "Outdoor Adventure Week",
        "description_uk": "Досліджуй природу, грай на свіжому повітрі, вчись орієнтуватись!",
        "description_en": "Explore nature, play outside, learn navigation!",
        "target_age_min": 36,
        "target_age_max": 144,
        "materials_shopping_list": [
            "magnifying glass", "bucket", "chalk", "ball", "rope", "compass (optional)",
            "paper", "pencil", "binoculars (optional)", "water bottles",
        ],
        "day_plans": {
            "monday": {
                "theme_uk": "Полювання на скарби",
                "theme_en": "Treasure Hunt",
                "activities": [
                    {
                        "title_uk": "Квест по двору або парку",
                        "title_en": "Backyard or park treasure hunt",
                        "duration_minutes": 45,
                        "description_en": "Parent hides clues around the yard/park, each clue leads to the next. Final clue leads to a small treasure (treat or toy). Requires adult supervision.",
                        "materials": ["paper", "pencil", "small prize"],
                    },
                ],
            },
            "tuesday": {
                "theme_uk": "Дослідник природи",
                "theme_en": "Nature Explorer",
                "activities": [
                    {
                        "title_uk": "Колекція листя та природних знахідок",
                        "title_en": "Leaf and nature collection walk",
                        "duration_minutes": 40,
                        "description_en": "Go on a nature walk and collect interesting leaves, stones, feathers, and flowers. At home, arrange them and create a nature collage or identification chart. Requires adult supervision.",
                        "materials": ["bag for collecting", "paper", "glue", "magnifying glass"],
                    },
                ],
            },
            "wednesday": {
                "theme_uk": "Спортивний день",
                "theme_en": "Sports Day",
                "activities": [
                    {
                        "title_uk": "Олімпійські ігри вдома",
                        "title_en": "Backyard Olympics",
                        "duration_minutes": 60,
                        "description_en": "Set up stations: running race, long jump, ball throw, obstacle course. Keep score and award medals (made from cardboard and ribbon). Requires adult supervision.",
                        "materials": ["ball", "chalk", "rope", "cardboard for medals", "ribbon"],
                    },
                ],
            },
            "thursday": {
                "theme_uk": "Орієнтування",
                "theme_en": "Navigation Day",
                "activities": [
                    {
                        "title_uk": "Намалюй карту свого двору",
                        "title_en": "Draw a map of your yard/neighborhood",
                        "duration_minutes": 40,
                        "description_en": "Walk around your yard or block. Draw a map with landmarks, trees, houses. Mark north/south. Older kids can use a compass. Requires adult supervision.",
                        "materials": ["paper", "pencil", "compass (optional)"],
                    },
                ],
            },
            "friday": {
                "theme_uk": "Пікнік дослідника",
                "theme_en": "Explorer's Picnic",
                "activities": [
                    {
                        "title_uk": "Пікнік з іграми на свіжому повітрі",
                        "title_en": "Outdoor picnic with games",
                        "duration_minutes": 90,
                        "description_en": "Pack a picnic, bring a blanket, and enjoy lunch outside. Play frisbee, tag, or just lie on the grass and watch clouds. A perfect way to end adventure week! Requires adult supervision.",
                        "materials": ["picnic blanket", "food", "frisbee or ball", "water"],
                    },
                ],
            },
        },
    },
]


async def seed_themed_weeks(db):
    from app.models.activity import ThemedWeek
    from sqlalchemy import select

    result = await db.execute(select(ThemedWeek).limit(1))
    if result.scalar_one_or_none():
        return  # already seeded

    for week_data in THEMED_WEEKS_DATA:
        week = ThemedWeek(**week_data)
        db.add(week)

    await db.commit()
    print(f"Seeded {len(THEMED_WEEKS_DATA)} themed weeks")
