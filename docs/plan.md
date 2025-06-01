Analyzing the whole project, feel free to delete or create a file(s) based on need. I need your best effort for this project.

I am working on a Flask app, website/web-app. Project is called AgroMap Uzbekistan as of now. I need help with README.md. I will give you the description of the project and a lot of other information about the project and what I want to do. Here is the information:

Agriculture in Uzbekistan is 1/5 of the annual GDP. Most farmers are small farms and majority of people in non-city areas engage in agriculture. Even big farmers lease out their land to multiple people for single season after harvesting their main crops.

People just plant whatever crop they are accustomed to planting or based on last season's prices. Uneducated decision making of what crop to plant results in some crops being overplanted and other crops being underplanted. For example, when many small farmers plant potato without realizing that so many other farmers are also planting potato, and as a result, there is an oversupply of some produces, resulting in price drops, hurting farmer's expected profits. Every year, this happens to some crops and so much of those crops rot in their fields without being harvested. Because, the cost of brining it to the market surpasses the profit they make by selling. So, there is a loss of income, and wasting of some crops/produces.

On the other hand, some other produces are not planted enough and because of lack of supply, price skyrocket and business men will bring those produces from neighboring countries to meet the local demand and profit off of high prices.

Loss of income for farmers, wasting of crops/produces and the need to import high in-demand produces from abroad prompted me to solve this problem. 

So, i want to build a website or web-app to better inform the farmers and help them make a more informed decision when it comes to what crop to plan and for how much field before a specific season.

When a user visits the web-app, it should show the map view of their region. I want to also approximately place the user on that same map by parsing their IP address. It's doesn't have to be precise, general location is ok. I want to collect very minimal data from users, such as what crop you are planting or planted and size of the field. Then, I place a heat-map or some indication that a specific crop is being planted or have been planted in a approximate location or region. 

Users should be able to see how much of any available crop is being planted or have been planted in their region. 

When we collect enough data about the type of crops and their approximate expected amount, we can make predictions on how much of a certain produce/crop will be available during the season. Since, we know have an expected amount of different crops, we can also predict upcoming prices of those crops/produces, by taking into account many other variables like current price, inflation, weather anomalies, or anything that could influence the price of those produces/crops.

This information will allow farmers to make better decisions as to what to plant for a season and how much to plant. Since, they can see the predicted, expected price and availability, this decision will better ensure their income and prevent unnecessary waste of resources. 

After, users provide us with 2 simple data: what crop, how much land, we can place them on the map and use heat-map to show the amount of specific crop being planted in a specific region. 

This way, the government of Uzbekistan and relevant departments also get a clearer picture of how the cultivatable land is being used and better prepare for potential shortages of certain crops/produces. 

The more data we collect from users, the better our predictive models become. We can show the historical, current and expected prices and trends of crops and produces in a specific region.


Another problem I would like to solve with this same web-app is the following. Google maps, OpenStreetMap, Apple Map, Here Map, Yandex Map all lack fine details on the map. I think Google, Apple or Yandex are not allowed to come to Uzbekistan and collect mapping data.

 So, my web-app will have another use-case. An important and useful one. When a user visits the web-app, as I previously stated, a local region map opens and they could be placed on a map either using their location or parsing their IP addresses. For example, a user sees their own location on the map through a dot or just by searching, zooming-in, they can click on their house and see that there is no address or street name. So, users should be able to suggest street names, building numbers, and business names. Once, we learn the street name and at least some building numbers, we can extrapolate the missing numbers for buildings from existing data. The more users suggest, the better the map details become. So, it will be publicly sourced map improvement and publicly sourced price prediction system. 

I would like the web-app to be clean, visually satisfying and minimalist in design. Almost all the target audience use smartphones and mostly android. No need for registering, or any hassle.


## 1. Project Vision at a Glance

**Name (working title):**  
AgroMap Uzbekistan

**Core Features:**
1. **Interactive Regional Map** (with approximate user location)
2. **Crop Planting Reporting:**  
   - Simple input: crop name, field size
   - Points heat-mapped by crop/size
3. **Crop Trends & Price Prediction:**  
   - Visualization of current, past, and predicted crop distribution and pricing trends
4. **Map Crowdsourcing:**  
   - Users can suggest new street/building/business info to improve detail
5. **Minimal Friction:**  
   - No registration required; clean, mobile-first design
   - Data optional and anonymous

---

## 2. Stack & Tech Recommendations

- **Frontend:**  
  - React, Vue, or Svelte (for interactive, mobile-focused UI)
  - Leaflet.js with OpenStreetMap tiles for mapping
  - Heatmap overlays for crop data
  - [Optional] Mapbox (if you want fancier visuals, but OSM is free and open)

- **Backend:**  
  - Python (Flask or FastAPI)
  - REST endpoints for submitting and retrieving crop data and map update suggestions
  - PostgreSQL (+PostGIS for geospatial features) or even just SQLite for MVP

- **Deployment:**  
  - Start with something simple like Heroku, Railway, or Vercel for MVP
  - Later, migrate to scalable cloud (AWS/GCP/Azure) if needed

- **Analytics & Prediction:**  
  - Python scripts using pandas for simple initial predictions
  - Optionally Jupyter/Colab for iterating on data analysis and ML

---

## 3. Suggested MVP Feature Roadmap

1. **Landing+Map Page**
    - Show Uzbekistan map based on IP/geolocation (Leaflet.js + OSM)
    - Minimal UX, mobile-first

2. **Data Input**
    - Form: “What crop are you planting?” and “How much land?”  
    - Auto-locate via browser or IP (city/region-level is okay to start)
    - Submit button overlays the data as a marker/intensity on the map

3. **Visualize Crops**
    - Aggregate submitted data and visualize (by crop/amount/region) on a heatmap layer

4. **Map Crowdsourcing**
    - Overlay button: “Suggest Street/Building/Business”
    - Mini-form pops up, and users drop a pin & describe the addition

5. **Historical/Predicted Trends** (can be basic for MVP)
    - Tab/page: Shows very simple aggregated statistics and a line plot/chart for the most popular crops

