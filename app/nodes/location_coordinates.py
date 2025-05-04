            print(f"Error parsing API response for {query}: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error for {query}: {str(e)}")
            return None
    
    async def get_coordinates_for_places(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get coordinates for a list of places.
        
        Args:
            places: List of place dictionaries with at least a 'name' key
            
        Returns:
            List of places with added 'coordinates' key
        """
        places_with_coords = []
        
        for place in places:
            if "name" not in place:
                continue
                
            coords = await self.get_coordinates(place["name"])
            if coords:
                place["coordinates"] = coords
            places_with_coords.append(place)
        
        return places_with_coords 