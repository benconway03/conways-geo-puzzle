import pandas as pd
import numpy as np
from IPython.display import display
import math
import random

class GeoGame:

    def calculate_haversine_distance(self, lat1, lon1, lat2, lon2):
        # 1. Radius of the Earth in kilometers (use 3958.8 for miles)
        R = 6371.0 

        # 2. Convert all decimal degrees to radians
        # (Python's trig functions require radians, not degrees)
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # 3. Calculate the differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # 4. Apply the Haversine formula
        a = math.sin(dlat / 2)**2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * \
            math.sin(dlon / 2)**2
            
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # 5. Multiply by Earth's radius to get the final distance
        distance = R * c
        
        return distance

    def get_direction(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dLon = lon2 - lon1
        y = math.sin(dLon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - \
            math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
        
        initial_bearing = math.atan2(y, x)
        
        # Convert from radians to degrees and normalize to 0-360
        bearing = (math.degrees(initial_bearing) + 360) % 360
        
        # Map degrees to compass points
        directions = ["North ⬆️", "North-East ↗️", "East ➡️", "South-East ↘️", 
                    "South ⬇️", "South-West ↙️", "West ⬅️", "North-West ↖️"]
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

    def guess_country(self, country):
            if country == self.target:
                # FIX: Return a tuple of two items so the unpacking works!
                return "You Won", "" 
            
            dist, bearing = self.country_dist(self.target, country)
            
            return dist, bearing
    

import difflib # Add this to your imports at the very top!

# --- Your exact GeoGame class goes here ---

if __name__ == "__main__":
    game = GeoGame()
    
    # Extract a list of all valid countries to use for spell-checking
    valid_countries = game.df_countries['COUNTRY'].tolist()
    
    print("\n🌍 Welcome to GeoGame!")
    print("Type 'quit' at any time to exit.")

    while True:
        user_guess = input("\nEnter a country: ").strip()
        
        if user_guess.lower() == 'quit':
            print(f"The answer was {game.target}. Thanks for playing!")
            break
            
        # 1. EXACT MATCH CHECK (Using .title() to fix basic capitalization)
        formatted_guess = user_guess.title()
        
        if formatted_guess in valid_countries:
            final_guess = formatted_guess
            
        else:
            # 2. FUZZY MATCH CHECK (Did they make a typo?)
            # get_close_matches returns a list of the closest words
            matches = difflib.get_close_matches(formatted_guess, valid_countries, n=1, cutoff=0.7)
            
            if matches:
                # If it found a close match, assume that's what they meant
                final_guess = matches[0]
                print(f"(Assuming you meant: {final_guess})")
            else:
                print("❌ Country not found in database. Check spelling!")
                continue
            
        # Send the verified, perfectly spelled guess into your class
        dist, bearing = game.guess_country(final_guess)
        
        if dist == "You Won":
            print(f"🎉 You Won! {final_guess} is correct!")
            break
        else:
            print(f"❌ {final_guess} is {dist} away. Head {bearing}")