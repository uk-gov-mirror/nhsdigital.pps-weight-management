from django.core.management.base import BaseCommand
from django.db import connection, transaction
import os, tempfile

# Auto-generated from /wm_rest_api/instance/services_v1.db

V1_ACTION_TYPE = [
    (1, 'app store'),
    (2, 'action link'),
    (3, 'clinical referral'),
]
V1_SERVICE_TYPE = [
    (1, 'Community event'),
    (2, 'Digital app'),
    (3, 'Weight-loss programme'),
    (4, 'Club'),
    (5, 'Online workouts'),
    (6, 'Gyms and leisure centres'),
]
V1_HELPS_WITH = [
    (1, 'managing weight'),
    (2, 'getting motivated'),
    (3, 'moving more and getting active'),
    (4, 'getting support from others'),
    (5, 'mental health, stress and anxiety'),
]
V1_WHO_FOR = [
    (1, 'Anyone aged 5 or over'),
    (2, 'Anyone'),
    (3, 'People aged 18 or over'),
    (4, 'People with a BMI over 30 (or  27.5 for people from black, Asian, and ethnic minority backgrounds)'),
    (5, 'People who have have diabetes, high blood pressure, or both'),
    (6, 'Men age 18 or over with a BMI of 27.50 or over'),
]
V1_WHO_NOT_FOR = [
    (1, 'People who are pregnant'),
    (2, 'Anyone with a BMI lower than 18.5'),
]
V1_MITIGATIONS = [
    (1, 'none'),
    (2, 'primary care'),
]
V1_TIME_REQUIRED = [
    (1, 'Every Saturday morning'),
    (2, '30 minutes'),
    (3, '3 times a week'),
    (4, '9 weeks total'),
    (5, '10 minutes a day'),
    (6, '12 weeks total'),
    (7, '30 minutes or less'),
    (8, '4 to 5 times a week (or whatever fits in with your lifestyle)'),
    (9, '3 months'),
    (10, 'Once a week'),
    (11, 'Sessions from 5 minutes to 30 minutes'),
    (12, 'Sessions from 10 minutes to 1 hour'),
]
V1_ACCESS = [
    (1, 'Online'),
    (2, 'Local gyms'),
    (3, 'On demand app'),
    (4, 'Local in-person events'),
    (5, 'Using the app with access to an online community'),
    (6, 'Local in-person group workshops with a coach'),
    (7, 'Online Zoom group workshops with coaching'),
    (8, 'GP referral'),
    (9, 'Using the app to access a weight loss plan'),
    (10, 'Using the app to scan food'),
    (11, 'Local, in-person group'),
    (13, 'Live workouts online'),
    (14, 'Website with access to an online community'),
    (15, '1-2-1 daily coaching is available'),
    (16, 'Online workouts with access to a Facebook group for registered members'),
    (17, '276 local leisure centres'),
]
V1_COSTS = [
    (1, 'Free'),
    (2, '30-day free trial'),
    (3, '"Core" plan from £6.50 a month'),
    (4, '"Core" plan with group workshops from £9.55 a month'),
    (5, 'Monthly  plan: £13.49 a month'),
    (6, 'Yearly plan: 7-day free trial then £80.99 a year (or £6.75 a month)'),
    (7, 'Buddy plan: £107.99 for 2 yearly subscriptions'),
    (8, 'Digital membership from £55 for 3 months'),
    (9, 'Group membership from £59.50 for 12 weeks'),
    (10, '£1 a week for 3 months'),
    (11, 'Standard plan £13 a month'),
    (12, '1-2-1 coached plan £26 a month'),
    (13, 'First month half price'),
    (14, 'From £35 a month'),
    (16, '£10 a month'),
    (17, 'From £10 a month'),
    (18, 'Free access to 10 beginner level programmes'),
    (19, '50% off subscriptions forever'),
    (20, 'From £4.99 a month'),
    (21, '3-day free trial'),
    (22, 'Free 1-day guest pass'),
    (23, 'Online access for £9.99 a month '),
    (24, 'Gym access with referral £15 a month '),
    (25, 'Standard membership from £25 a month '),
]
V1_TAXONOMY = [
    (1, 'free'),
    (2, 'self_led'),
    (3, 'in_a_group'),
    (4, 'venue_or_a_place'),
    (5, 'scheduled'),
    (6, 'in_real_life'),
    (7, 'following_a_plan'),
    (8, 'alone'),
    (9, 'wherever_works_for_you'),
    (10, 'self_paced_plan'),
    (11, 'initial_discount'),
    (12, 'paid_for'),
    (13, 'taught_by_a_person'),
    (15, 'digital'),
    (16, 'on_demand'),
    (17, 'one_to_one'),
    (18, 'permanent_discount'),
]

V1_SERVICE = [
    (1, 'Parkrun', """A free, weekly, timed 5k run (or walk) that happens in parks and open spaces around the country.
""", """<p>Parkruns are free, local 5k runs that anyone can enter.</p>
""", """<p>Parkruns usually happen at the same time and place, once a week. If you want your time to be recorded you&#39;ll need to register on the Parkrun website to get a personal ID. A volunteer will record your finishing time at the end.</p>
""", """<p>Doing parkruns regularly could help you improve your physical and mental health, and help you connect with your local community too.</p>
""", 'Free', 'Register Now', 'https://www.parkrun.org.uk/register/', None, None, 'https://www.parkrun.org.uk/', 'logo-parkrun.svg', None, 2, 1, 2.0),
    (2, 'NHS Couch to 5k', """The NHS Couch to 5k app guides you from the couch to running 5km in just 9 weeks.
""", """<p>Couch to 5k is a simple, free running plan for absolute beginners.</p>
""", """<p>A trainer will guide you as you start with a mix of running and walking.</p>

<p>In the first week, you&#39;ll start with 1 minute runs, followed by a 1 minute 30 second walk, going at a pace that feels right for you. Each week, you&#39;ll run a little more.</p>
""", """<p>By the end, you&#39;ll be running 5k with confidence, no matter your starting fitness level or when you last exercised.</p>
""", 'Free', None, None, 'https://play.google.com/store/apps/details?id=com.phe.couchto5K', 'https://itunes.apple.com/gb/app/one-you-couch-to-5k/id1082307672?mt=8', 'https://play.google.com/store/apps/details?id=com.phe.couchto5K', 'couch-to-5k-icon.png', 'couch-to-5k-promo.png', 1, 2, 1.0),
    (3, 'Weight Watchers', """A personalised plan with live and on-demand coaching to help you lose weight and stay healthy.
""", """<p>The Weight Watchers app provides a personalised nutrition plan, activity trackers and over 4,500 recipe ideas.</p>
""", """<p>Choose between a core membership or a membership with workshops. Both memberships include a 30-day free trial and a customised nutrition plan, activity trackers and recipes.</p>
""", """<p>If you&#39;re overweight, making small changes to what you are eating can drinking can help you lose weight. And it could help reduce the risk of developing health conditions like high blood pressure, heart disease and type 2 diabetes.</p>
""", 'Free trial then from £6.50 a month', 'Start a 30-day free trial here', 'Start a 30-day free trial here', None, None, 'https://www.weightwatchers.com/uk/', 'weight-watchers-logo.svg', None, 2, 3, 2.0),
    (4, 'NHS Active 10', """The free NHS Active 10 app anonymously records every minute of walking you do.
""", """<p>Active 10 is a free app that helps you fit short, brisk walks in to your day. Active 10 means 10 brisk minutes.</p>
""", """<p>Track all your walking and how many brisk minutes you&#39;ve walked in the Active 10 app. The app&#39;s Pace Checker will help you learn what brisk walking feels like.</p>

<p>You can set goals to keep you motivated and you&#39;ll earn rewards for every brisk minute you walk throughout the day.</p>
""", """<p>Just 10 minutes of brisk walking every day can get your heart pumping and can make you feel more energetic, as well as lowering your risk of serious illnesses like heart disease and type 2 diabetes.</p>

<p>Going for a brisk walk is a great way to clear your head and improve your mood. And it&#39;s easy to fit into your day, from taking the dog out to going for a lunchtime walk.</p>
""", 'Free', None, None, 'https://play.google.com/store/apps/details?id=uk.ac.shef.oak.pheactiveten', 'https://itunes.apple.com/gb/app/one-you-active-10-walking-tracker/id1204295312?mt=8', 'https://www.nhs.uk/better-health/get-active/', 'active-10-icon.png', 'active-10-promo.png', 1, 2, 1.0),
    (5, 'NHS Digital Weight Management Programme', """A 12-week online behavioural and lifestyle programme.
""", """<p>The NHS Digital Weight Management Programme supports adults living with obesity who also have a diagnosis of diabetes or hypertension to manage their weight and improve their health.</p>
""", """<p>You need to speak to your GP or a local pharmacist who can refer you to the programme.</p>

<p>You choose a weight management plan to help you develop healthier eating habits, be more active and lose weight. Each plan provides recipes and nutrition advice, wellbeing support and tips to boost your activity levels. As an online plan, you can do it anywhere in your own time.</p>
""", """<p>This programme supports you to start building healthy habits so you can eat, sleep and feel better.</p>
""", 'Free', None, None, None, None, 'https://www.england.nhs.uk/digital-weight-management/', 'logo-nhs.png', None, 3, 3, 2.1),
    (6, 'NHS Weight Loss Plan', """An app to help you start eating more healthily, being more active, and losing weight.
""", """<p>The NHS Weight Loss Plan gives you a 12-week plan that helps you:</p>

<ul>
	<li>set weight loss goals</li>
	<li>plan your meals</li>
	<li>make healthier food choices</li>
	<li>get more active and burn more calories</li>
	<li>record your activity and progress</li>
</ul>
""", """<p>Follow weekly NHS guides to help you maintain a balanced diet, and use the daily diary to monitor what you&rsquo;re eating and keep to a recommended calorie target.</p>

<p>The app will help you work out what a healthy weight is for you by using an in-app BMI calculator and help you set a healthy calorie target that&rsquo;s right for you.</p>

<p>Each weekly guide has actions, hints and tips for reaching your goal. To keep track of your progress you can log the food and calories you eat at each meal in the dairy, and you can record your weight each week to monitor your weight-loss.</p>
""", """<p>If you&#39;re overweight, making small changes to what you are eating can drinking can help you lose weight. And it could help reduce the risk of developing health conditions like high blood pressure, heart disease and type 2 diabetes.</p>
""", 'Free', None, None, 'https://play.google.com/store/apps/details?id=com.nhs.weightloss', 'https://apps.apple.com/gb/app/id1519208548', 'https://www.nhs.uk/better-health/lose-weight/', 'nhs-weightloss-app-logo.png', 'nhs-weightloss-app-promo.png', 1, 2, 1.0),
    (7, 'NHS Food Scanner', """A food scanning app to help you find healthier swaps for the next time you shop.
""", """<p>The NHS Food Scanner lets you scan the barcode on a product&#39;s packaging using your phone&#39;s camera. The app will then tell you if there are any healthier options available.</p>
""", """<p>The app will show you things like:</p>

<ul>
	<li>whether a product is a &#39;good choice&#39;</li>
	<li>traffic light ratings so know if a product is high, medium or low in sugar, salt and fat</li>
	<li>the full list of every product you&#39;ve ever scanned</li>
</ul>
""", """<p>Making better food and drink choices could help you and your family stay healthy.</p>
""", 'Free', None, None, 'https://play.google.com/store/apps/details?id=com.phe.c4lfoodsmart&hl=en_GB', 'https://apps.apple.com/gb/app/change4life-food-scanner/id1182946415', 'https://www.nhs.uk/healthier-families/food-facts/nhs-food-scanner-app/', 'nhs-food-scanner-app-logo.png', 'nhs-food-scanner-app-promo.png', 1, 2, 1.0),
    (8, 'Fit Fans', """A health programme that provides free, weekly sessions at your local football club.
""", """<p>Football clubs across the country offer a free health programme for people who want to lose weight, get fitter and lead a healthier, more active life.</p>
""", """<ul>
	<li>Go to weekly sessions at your local football club.</li>
	<li>Meet other football fans on the same journey as you.</li>
	<li>Learn how to make better choices to improve your lifestyle and health.</li>
	<li>Be supported through your journey by club staff.</li>
</ul>

<p>&nbsp;</p>
""", """<p>Making long-term improvements in weight loss, physical activity, diet and general wellbeing can help you stay healthy for longer.</p>
""", 'Free', 'Find out more', 'https://eflinthecommunity.com/fitfans/', None, None, None, 'efl-fit-fans-logo.png', None, 2, 4, 2.0),
    (9, 'The Body Coach', """An app to help you improve your fitness with quick workouts for all abilities and simple, tasty recipes.
""", """<p>The Body Coach app provides:</p>

<ul>
	<li>a structured workout programme for your ability</li>
	<li>recipes tailored to your body and goals</li>
	<li>live workouts with Joe and Body Coach trainers</li>
	<li>access to the Body Coach community</li>
</ul>
""", """<p>When you sign up, you&#39;ll answer a few quick questions so you can get a plan that&#39;s tailored to you.</p>

<p>Based on your current fitness level, you&#39;ll get a structured workout plan and a set of recipes with portions tailored specifically to you and your goals.</p>

<p>Every month, you&#39;ll get access to new workouts to help build on your fitness and strength, along with a set of new recipes so you keep making progress.</p>
""", """<p>The programme is designed to help you improve your fitness, but it can also have a big impact on your energy, happiness and overall health.</p>
""", 'Free trial then discounts. From £6.75 a month.', '10% offer', 'Free trial then discounts. From £6.75 a month.', None, None, 'https://www.thebodycoach.com/', 'the-body-coach-logo.svg', None, 2, 2, 2.0),
    (10, 'Slimming World', """A weight-loss programme providing mindset-shifting, habit-changing support that will get you to your weight-loss target and help you stay there.
""", """<p>You can choose a group or online membership to help you reach your weight-loss target. Both memberships offer:</p>

<ul>
	<li>more than 2,000 exclusive Slimming World recipes</li>
	<li>meal plans, weight-loss tools, strategies, and articles</li>
	<li>on-demand exercise videos tailored to your activity level</li>
	<li>a barcode scanner to help you make good food choices</li>
</ul>
""", """<p>The group membership is for people who would like the accountability, friendship and in-person support and community of other slimmers. Your local Slimming World consultant and friends in group will be there to cheer you on every step of the way on your weight loss journey.&nbsp;&nbsp;</p>

<p>The digital&nbsp;service, Slimming World Online, is good if you need a little more flexibility. There&#39;s a community of online members for support and encouragement (when you want it), and unlimited access to digital live events for extra motivation.&nbsp;</p>
""", """<p>The programme can help you reach the weight you want to be &ndash; you choose your own target. By following a tailored plan, you can build healthy habits that last.</p>
""", 'From £55 for 3 months.', 'Discounted membership', 'https://www.slimmingworld.co.uk/betterhealth', None, None, 'https://www.slimmingworld.co.uk/', 'slimming-world-logo.png', None, 2, 3, 2.0),
    (11, 'GetSlim', """An online weight-loss app to help you get fitter and healthier.
""", """<p>The GetSlim online weight-loss club offers a:</p>

<ul>
	<li>weight-loss tracker</li>
	<li>food and fitness diary</li>
	<li>choice of diet plans</li>
	<li>community of coaches and members</li>
</ul>
""", """<p>Sign up to the the standard monthly subscription plan to get access to the GetSlim app.</p>

<p>You can set targets to keep you motivated and get support from people to help you keep going.</p>
""", """<p>The programme can help you build a healthier lifestyle and get to the weight you want to be.</p>
""", '£1 a week for 3 months then £13 a month.', 'TEXT OFFER', 'https://www.getslim.co.uk/betterhealth', None, None, 'https://www.getslim.co.uk/', 'get-slim-logo.svg', None, 2, 3, 2.0),
    (12, 'MAN V FAT Football', """A weight-loss programme for football-loving men.
""", """<p>MAN V FAT Football helps men across the country lose weight and improve their health through:</p>

<ul>
	<li>playing football</li>
	<li>getting team support</li>
	<li>an app with useful articles and recipes</li>
	<li>mental health support</li>
	<li>over 200 online gym classes</li>
</ul>
""", """<p>After you sign up to your local club, you&#39;ll get access to the online app and online gym classes straightaway.</p>

<p>Next, you&rsquo;ll get a text from your coach before you&rsquo;re assigned to a team. Then you can start your first club session.</p>
""", """<p>Playing football and spending time with a supportive team can help you lose weight, make friends, get fitter and improve your health.</p>
""", 'First month half price then £35 a month.', 'Register now for first month half price', 'https://manvfat.com/better-health/', None, None, 'https://manvfat.com/better-health/', 'man-v-fat-logo.svg', None, 2, 4, 2.0),
    (13, 'Healthier for Life', """An online, plant-based weight-loss club.
""", """<p>Healthier for Life provides a food and exercise diary based on plant-based eating, with coaching support and vegan recipes.</p>
""", """<p>Choose the quarterly subscription plan so you can:</p>

<ul>
	<li>monitor your progress with tracking tools</li>
	<li>get flexible, healthy eating plans and over 1200 recipes</li>
	<li>get nutritional coaches to support, inspire and motivate you 7 days a week</li>
	<li>do cardio, strength &amp; stability workouts for all levels</li>
	<li>access health, wellness and exercise articles</li>
</ul>
""", """<p>Making long-term, healthy changes following a plant-based can help you become fitter and healthier.</p>
""", '£1 a week for 3 months then £10 a month.', 'Register now for £1 a week for 3 months', 'https://www.healthierforlife.com/better-health', None, None, 'https://www.healthierforlife.com/', 'healthier-for-life.png', None, 2, 3, 2.0),
    (14, 'Couch to Fitness', """Online workout plans to suit your fitness level.
""", """<p>Couch to Fitness provides a free online workout plan that you can do at home, in your own time.</p>
""", """<p>Expert instructors guide you through 30-minute sessions 3 times a week. The sessions are suitable for different fitness levels and you don&#39;t need any equipment.</p>
""", """<p>Doing these workouts regulary can help you get fitter and healthier at a pace that suits you.</p>
""", 'Free', 'Start now', 'https://couchtofitness.com/', None, None, None, 'couch-to-fitness-logo.png', None, 2, 5, 2.0),
    (15, 'Better Leisure centres', """Fitness centres around the country providing access to exercise classes and fitness facilities.
""", """<p>Better Leisure Centres offer a range of activities to help you move more, including:</p>

<ul>
	<li>swimming</li>
	<li>the gym</li>
	<li>exercise classes</li>
</ul>
""", """<p>Find your local Better Leisure centre and choose the activities or memberships that work for you.</p>

<p>Some centres provide creche facilities for under 5s so you can do an activity while your children are being looked after.</p>
""", """<p>However you choose to be active, doing exercise regularly can help you get fit and stay healthy.</p>
""", 'From £10 a month.', 'Find out more', 'https://www.better.org.uk/healthy-communities/better-health-for-me?utm_source=phe&utm_medium=affiliate&utm_campaign=betterhealth', None, None, 'https://www.better.org.uk/', 'better-logo.svg', None, 2, 6, 2.0),
    (16, 'Instructor Live', """A fitness platform with classes designed for beginners.
""", """<p>The Instructor Live beginners package includes classes like:</p>

<ul>
	<li>high intensity interval training (HIIT) for beginners</li>
	<li>introduction to pilates</li>
	<li>dance HIIT for beginners</li>
	<li>beginners aerobics</li>
	<li>daily meditation practice</li>
	<li>yoga basics</li>
	<li>introduction to weights</li>
</ul>
""", """<p>You can access these classes as often as you like for 3 months. It&#39;s a self-paced, online course, so you decide when you start and finish.</p>
""", """<p>If you&#39;re new to working out, or haven&#39;t done much exercise in a while, these beginner classes can help ease you in to getting fitter and more active.</p>
""", 'Free beginner classes for 3 months then from £4.99 a month.', 'Get started now', 'https://app.instructorlive.com/p/better-health-beginners-package', None, None, 'https://www.instructorlive.com/', 'instructor-live-logo.png', None, 2, 5, 2.0),
    (17, 'Anytime Fitness', """Gyms around the country that are open 24/7.
""", """<p>Anytime Fitness provides gym facilities, group training classes and supportive coaches.</p>
""", """<p>Find a club near you and use a free 3-day pass so you can:</p>

<ul>
	<li>discuss your health goals with one of the Anytime Fitness team</li>
	<li>be taken on a club tour to see the range of exercise options and support available to you</li>
	<li>enjoy some free workouts and see if a fitness membership is for you</li>
</ul>
""", """<p>You can get fitter and healthier in a way that fits in with your life.</p>
""", 'Free trial', 'Get a 3-day free trial now', 'https://www.anytimefitness.co.uk/betterhealth-campaign/', None, None, 'https://www.anytimefitness.co.uk/', 'anytime-fitness-logo.png', None, 2, 6, 2.0),
    (18, 'Everyone Active', """Fitness centres with different memberships to suit different needs.
""", """<p>Everyone Active provides gyms, pools, exercise classes and wellness memberships.</p>
""", """<p>You can choose from:</p>

<ul>
	<li>an exercise referral programme, which is for people living with long-term health conditions</li>
	<li>guest day passes</li>
	<li>an app, which gives you access to services like exercise classes and personal training</li>
</ul>
""", """<p>Finding a way to get active could help you improve your overall physical and mental health and wellbeing.</p>
""", 'Free 1-day pass. Memberships from £9.99 a month.', 'Find out more', 'https://www.everyoneactive.com/better-health-everyone-active/', None, None, 'https://www.everyoneactive.com/', 'everyone-active-logo.svg', None, 2, 6, 2.0),
]

V1_SERVICE_HELPS_WITH = [
    (1, 1),
    (1, 3),
    (1, 2),
    (1, 4),
    (2, 5),
    (2, 1),
    (2, 2),
    (2, 3),
    (3, 2),
    (3, 3),
    (3, 1),
    (4, 2),
    (4, 3),
    (4, 1),
    (4, 5),
    (5, 3),
    (5, 1),
    (5, 2),
    (6, 3),
    (6, 1),
    (6, 2),
    (7, 2),
    (7, 1),
    (8, 5),
    (8, 3),
    (8, 1),
    (8, 2),
    (9, 5),
    (9, 1),
    (9, 3),
    (9, 2),
    (10, 1),
    (10, 5),
    (10, 2),
    (10, 3),
    (11, 1),
    (11, 2),
    (11, 3),
    (12, 1),
    (12, 3),
    (12, 2),
    (12, 5),
    (13, 3),
    (13, 2),
    (13, 1),
    (14, 3),
    (14, 5),
    (14, 1),
    (14, 2),
    (15, 2),
    (15, 1),
    (15, 3),
    (16, 5),
    (16, 1),
    (16, 2),
    (16, 3),
    (17, 3),
    (17, 1),
    (17, 2),
    (18, 3),
    (18, 1),
    (18, 2),
]
V1_SERVICE_WHO_FOR = [
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 2),
    (5, 3),
    (5, 4),
    (5, 5),
    (6, 3),
    (7, 2),
    (8, 2),
    (9, 3),
    (10, 3),
    (11, 3),
    (12, 6),
    (13, 3),
    (14, 3),
    (15, 2),
    (16, 3),
    (17, 3),
    (18, 3),
]
V1_SERVICE_WHO_NOT_FOR = [
    (3, 1),
    (3, 2),
    (6, 1),
    (6, 2),
    (9, 1),
    (10, 1),
]
V1_SERVICE_MITIGATIONS = [
    (1, 1),
    (2, 2),
    (3, 2),
    (4, 1),
    (5, 2),
    (6, 2),
    (7, 1),
    (8, 1),
    (9, 2),
    (10, 2),
    (11, 2),
    (12, 2),
    (13, 1),
    (14, 1),
    (15, 2),
    (16, 2),
    (17, 2),
    (18, 2),
]
V1_SERVICE_TIME_REQUIRED = [
    (1, 1),
    (2, 2),
    (2, 3),
    (2, 4),
    (4, 5),
    (5, 6),
    (6, 6),
    (9, 7),
    (9, 8),
    (10, 9),
    (12, 10),
    (14, 11),
    (16, 12),
]
V1_SERVICE_ACCESS = [
    (1, 4),
    (3, 5),
    (3, 6),
    (3, 7),
    (5, 8),
    (6, 9),
    (7, 10),
    (8, 11),
    (9, 5),
    (9, 13),
    (10, 5),
    (11, 15),
    (11, 14),
    (12, 11),
    (13, 14),
    (14, 16),
    (15, 17),
    (16, 1),
    (17, 2),
    (18, 2),
    (18, 3),
]
V1_SERVICE_COSTS = [
    (1, 1),
    (2, 1),
    (3, 2),
    (3, 3),
    (3, 4),
    (4, 1),
    (5, 1),
    (6, 1),
    (7, 1),
    (8, 1),
    (9, 5),
    (9, 6),
    (9, 7),
    (10, 9),
    (11, 10),
    (11, 12),
    (11, 11),
    (12, 13),
    (12, 14),
    (13, 10),
    (13, 16),
    (14, 1),
    (15, 17),
    (16, 18),
    (16, 19),
    (16, 20),
    (17, 21),
    (18, 22),
    (18, 24),
    (18, 23),
    (18, 25),
]
V1_SERVICE_TAXONOMY = [
    (1, 1),
    (1, 2),
    (1, 3),
    (1, 4),
    (1, 5),
    (1, 6),
    (2, 1),
    (2, 6),
    (2, 7),
    (2, 8),
    (2, 9),
    (2, 10),
    (3, 2),
    (3, 3),
    (3, 4),
    (3, 5),
    (3, 6),
    (3, 7),
    (3, 8),
    (3, 9),
    (3, 10),
    (3, 11),
    (3, 12),
    (3, 13),
    (3, 15),
    (4, 1),
    (4, 2),
    (4, 6),
    (4, 7),
    (4, 8),
    (4, 9),
    (4, 10),
    (5, 1),
    (5, 2),
    (5, 7),
    (5, 8),
    (5, 9),
    (5, 10),
    (5, 15),
    (6, 1),
    (6, 2),
    (6, 7),
    (6, 8),
    (6, 9),
    (6, 10),
    (6, 15),
    (7, 8),
    (7, 15),
    (7, 1),
    (7, 16),
    (7, 2),
    (7, 10),
    (7, 9),
    (8, 1),
    (8, 3),
    (8, 6),
    (8, 5),
    (8, 10),
    (8, 13),
    (8, 4),
    (9, 8),
    (9, 15),
    (9, 7),
    (9, 11),
    (9, 16),
    (9, 12),
    (9, 2),
    (9, 13),
    (9, 9),
    (10, 8),
    (10, 15),
    (10, 7),
    (10, 3),
    (10, 6),
    (10, 11),
    (10, 12),
    (10, 5),
    (10, 2),
    (10, 10),
    (10, 13),
    (10, 4),
    (10, 9),
    (11, 8),
    (11, 15),
    (11, 7),
    (11, 3),
    (11, 11),
    (11, 16),
    (11, 12),
    (11, 2),
    (11, 10),
    (11, 9),
    (12, 3),
    (12, 6),
    (12, 11),
    (12, 12),
    (12, 5),
    (12, 13),
    (12, 4),
    (13, 8),
    (13, 15),
    (13, 7),
    (13, 11),
    (13, 16),
    (13, 12),
    (13, 2),
    (13, 10),
    (13, 9),
    (14, 8),
    (14, 15),
    (14, 7),
    (14, 1),
    (14, 16),
    (14, 13),
    (14, 9),
    (15, 8),
    (15, 3),
    (15, 17),
    (15, 12),
    (15, 5),
    (15, 2),
    (15, 10),
    (15, 13),
    (15, 4),
    (16, 8),
    (16, 15),
    (16, 16),
    (16, 12),
    (16, 18),
    (16, 2),
    (16, 13),
    (16, 9),
    (17, 8),
    (17, 15),
    (17, 7),
    (17, 3),
    (17, 6),
    (17, 11),
    (17, 16),
    (17, 17),
    (17, 12),
    (17, 5),
    (17, 2),
    (17, 13),
    (17, 4),
    (17, 9),
    (18, 8),
    (18, 15),
    (18, 3),
    (18, 6),
    (18, 11),
    (18, 16),
    (18, 17),
    (18, 12),
    (18, 5),
    (18, 2),
    (18, 13),
    (18, 4),
    (18, 9),
    (15, 6),
]

def _emit_values(rows):
    def lit(v):
        if v is None:
            return "NULL"
        if isinstance(v, (int, float)):
            return str(v)
        return "'" + str(v).replace("'", "''") + "'"
    return ",\n    ".join("(" + ", ".join(lit(x) for x in row) + ")" for row in rows)

class Command(BaseCommand):
    help = "Insert built-in V1 data as INSERT statements (no-op if V1_SERVICE not empty). Also writes seed_v1.sql."

    def handle(self, *args, **options):
        with connection.cursor() as cur:
            cur.execute('SELECT COUNT(1) FROM "V1_SERVICE";')
            (count,) = cur.fetchone()
            if count and count > 0:
                self.stdout.write(self.style.HTTP_INFO("V1_SERVICE already has data—skipping V1_seed_data."))
                return

        stmts = []
        def ins(table, cols, rows):
            if not rows:
                return
            cols_sql = ", ".join(['"' + c + '"' for c in cols])
            values_sql = _emit_values(rows)
            pk = cols[0]
            stmt = 'INSERT INTO "' + table + '" (' + cols_sql + ') VALUES\n    ' + values_sql + '\nON CONFLICT ("' + pk + '") DO NOTHING;'
            stmts.append(stmt)

        def ins_through(table, left, right, rows):
            if not rows:
                return
            cols_sql = '"' + left + '", "' + right + '"'
            values_sql = _emit_values(rows)
            stmt = 'INSERT INTO "' + table + '" (' + cols_sql + ') VALUES\n    ' + values_sql + '\nON CONFLICT DO NOTHING;'
            stmts.append(stmt)

        # Lookups
        ins("V1_ACTION_TYPE", ["id","type"], V1_ACTION_TYPE)
        ins("V1_SERVICE_TYPE", ["id","type"], V1_SERVICE_TYPE)
        ins("V1_HELPS_WITH", ["id","benefit"], V1_HELPS_WITH)
        ins("V1_WHO_FOR", ["id","target"], V1_WHO_FOR)
        ins("V1_WHO_NOT_FOR", ["id","target"], V1_WHO_NOT_FOR)
        ins("V1_MITIGATIONS", ["id","type"], V1_MITIGATIONS)
        ins("V1_TIME_REQUIRED", ["id","required"], V1_TIME_REQUIRED)
        ins("V1_ACCESS", ["id","type"], V1_ACCESS)
        ins("V1_COSTS", ["id","name"], V1_COSTS)
        ins("V1_TAXONOMY", ["id","term"], V1_TAXONOMY)

        # Service
        ins("V1_SERVICE", [
            "id","name","description","what_it_is","how_it_works","what_it_could_do",
            "cost_text","action_text","action_url","action_url_playstore","action_url_appstore","action_url_moreinfo",
            "logo_image","promo","action_id","service_type_id","sort_order"
        ], V1_SERVICE)

        # Throughs
        ins_through("V1_SERVICE_HELPS_WITH", "service_id", "helpswith_id", V1_SERVICE_HELPS_WITH)
        ins_through("V1_SERVICE_WHO_FOR", "service_id", "who_for_id", V1_SERVICE_WHO_FOR)
        ins_through("V1_SERVICE_WHO_NOT_FOR", "service_id", "who_not_for_id", V1_SERVICE_WHO_NOT_FOR)
        ins_through("V1_SERVICE_MITIGATIONS", "service_id", "mitigation_id", V1_SERVICE_MITIGATIONS)
        ins_through("V1_SERVICE_TIME_REQUIRED", "service_id", "time_id", V1_SERVICE_TIME_REQUIRED)
        ins_through("V1_SERVICE_ACCESS", "service_id", "access_id", V1_SERVICE_ACCESS)
        ins_through("V1_SERVICE_COSTS", "service_id", "cost_id", V1_SERVICE_COSTS)
        ins_through("V1_SERVICE_TAXONOMY", "service_id", "taxonomy_id", V1_SERVICE_TAXONOMY)

        # build sql_blob earlier as you already do...
        sql_blob = ";\n\n".join(stmts) + (";" if stmts else "")

        # Try to write to a safe place, but never fail if we can't.
        def _try_write_sql(blob: str, default_name: str):
            # 1) Respect an override path if provided
            out = os.environ.get("SEED_SQL_OUT") or os.path.join(tempfile.gettempdir(), default_name)
            try:
                with open(out, "w", encoding="utf-8") as f:
                    f.write(blob)
                self.stdout.write(self.style.HTTP_INFO(f"Wrote seed SQL to {out}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not write seed SQL file ({out}): {e}"))
                # continue — we will still execute the statements

        _try_write_sql(sql_blob, "seed_v1.sql")
        
        # Execute the statements regardless of file-write success
        with transaction.atomic():
            with connection.cursor() as cur:
                for stmt in stmts:
                    cur.execute(stmt)
        self.stdout.write(self.style.SUCCESS(f"Inserted V1 seed data ({len(stmts)} statements)."))
