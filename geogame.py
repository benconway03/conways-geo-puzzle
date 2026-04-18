import pandas as pd
import numpy as np
from IPython.display import display
import math
import random
import difflib
import time # Added the time module

class GeoGame:

    def calculate_haversine_distance(self, lat1, lon1, lat2, lon2):
        dLat = lat2 - lat1
        dLon = lon2 - lon1
        
        # 1. Map Wrap-Around: Force the math to take the shortest path across the date line
        dLon = (dLon + 180) % 360 - 180
        
        # 2. Latitude Squeeze: Longitude lines get closer together near the poles
        avg_lat = math.radians((lat1 + lat2) / 2.0)
        dLon_scaled = dLon * math.cos(avg_lat)
        
        # 3. Pythagorean theorem on the newly scaled flat map
        degree_distance = math.sqrt((dLat ** 2) + (dLon_scaled ** 2))
        
        # Convert to kilometers
        distance = degree_distance * 111.0
        
        return distance

    def get_direction(self, lat1, lon1, lat2, lon2):
        dLat = lat2 - lat1
        dLon = lon2 - lon1
        
        # Map Wrap-Around so the compass points the shortest way
        dLon = (dLon + 180) % 360 - 180
        
        # Latitude Squeeze so the compass angle doesn't get distorted
        avg_lat = math.radians((lat1 + lat2) / 2.0)
        dLon_scaled = dLon * math.cos(avg_lat)
        
        # Calculate the angle using the scaled flat coordinates
        initial_bearing = math.degrees(math.atan2(dLon_scaled, dLat))
        bearing = (initial_bearing + 360) % 360
        
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