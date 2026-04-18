import pandas as pd
import numpy as np
from IPython.display import display
import math
import random
import difflib
import time # Added the time module

class GeoGame:

    def calculate_haversine_distance(self, lat1, lon1, lat2, lon2):
        # Radius of the Earth in kilometers
        R = 6371.0 

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine formula
        a = math.sin(dlat / 2)**2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(dlon / 2)**2
            
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        
        return distance

    def get_direction(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dLon = lon2 - lon1
        y = math.sin(dLon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - \
            math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
        
        initial_bearing = math.atan2(y, x)
        
        bearing = (math.degrees(initial_bearing) + 360) % 360
        
        directions = ["North ⬆️", 
                      "North-East ↗️", 
                      "East ➡️", 
                      "South-East ↘️", 
                      "South ⬇️", 
                      "South-West ↙️", 
                      "West ⬅️", 
                      "North-West ↖️"]
        
        index = round(bearing / 45) % 8
        return directions[index]

    def gen_rand_country(self):
        random_number = random.randint(0, len(self.df_countries)-1)
        country = self.df_countries.iloc[random_number]['COUNTRY']
        return country
    
    def country_dist(self, co1, co2):
        coords1 = self.df_countries.loc[self.df_countries['COUNTRY'] == co1, ['latitude', 'longitude']].values[0]
        coords2 = self.df_countries.loc[self.df_countries['COUNTRY'] == co2, ['latitude', 'longitude']].values[0]

        target_lat1 = coords1[0]
        target_lon1 = coords1[1]

        target_lat2 = coords2[0]
        target_lon2 = coords2[1]

        dist = self.calculate_haversine_distance(target_lat1, target_lon1, target_lat2, target_lon2)

        bearing = self.get_direction(target_lat2, target_lon2, target_lat1, target_lon1)

        return f'{round(dist, 2)}km', bearing

    def __init__(self):
        self.df_countries = pd.read_csv('countries.csv')
        self.target = self.gen_rand_country()
        self.start_time = None # Initialize the timer variable

    def guess_country(self, country):
        # Start the timer on the very first valid guess
        if self.start_time is None:
            self.start_time = time.time()

        if country == self.target:
            # Calculate elapsed time and format it nicely
            elapsed = time.time() - self.start_time
            mins = int(elapsed // 60)
            secs = elapsed % 60
            
            if mins > 0:
                time_string = f"{mins}m {secs:.1f}s"
            else:
                time_string = f"{secs:.1f}s"
                
            # Pass the time_string back instead of an empty string
            return "You Won", time_string 
        
        dist, bearing = self.country_dist(self.target, country)
        
        return dist, bearing


if __name__ == "__main__":
    game = GeoGame()
    
    valid_countries = game.df_countries['COUNTRY'].tolist()
    
    print("\n🌍 Welcome to GeoGame!")
    print("Type 'quit' at any time to exit.")

    while True:
        user_guess = input("\nEnter a country: ").strip()
        
        if user_guess.lower() == 'quit':
            print(f"The answer was {game.target}. Thanks for playing!")
            break
    
        formatted_guess = user_guess.title()
        
        if formatted_guess in valid_countries:
            final_guess = formatted_guess
            
        else:
            matches = difflib.get_close_matches(formatted_guess, valid_countries, n=1, cutoff=0.7)
            
            if matches:
                final_guess = matches[0]
                print(f"(Assuming you meant: {final_guess})")
            else:
                print("❌ Country not found in database. Check spelling!")
                continue

        dist, bearing = game.guess_country(final_guess)
        
        if dist == "You Won":
            # The 'bearing' variable holds our formatted time_string on a win
            print(f"🎉 You Won! {final_guess} is correct!")
            print(f"⏱️ Time taken: {bearing}")
            break
        else:
            print(f"❌ {final_guess} is {dist} away. Head {bearing}")