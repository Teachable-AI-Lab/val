import sys
import websocket
import importlib
import json
import math

class VerticalFarmEnv():

    def __init__(self, url='replace_url'):
        pass

    def send_and_recv(self, message: dict):
        message = json.dumps(message)
        attempts = 0
        while attempts < 3:
            try:
                self.ws.send(message)
                result = self.ws.recv()
                return json.loads(result)
            except:
                print(attempts)
                attempts = attempts + 1
                self.ws = websocket.create_connection(self.url)

        print("Failed")
        return None
    
    def get_state_from_game(self):
        state = self.send_and_recv({'command':'get_state'})
        return state
    
    def execute_action(self):
        pass

    def find_nearest_target(self):
        cur_state = self.get_state_from_game()
        #TODO: calculate the target location for these actions 
        # if target is not given: harvet, pluck, sample, plant

    def stop(self):
        """cancels the bot’s current command queue then immediately ends"""

        command = {
            'command':'execute_action',
            'action':'stop'
        }
        result = self.send_and_recv(command)

        print("Result of stopping bot: ", result)
        return result["Status"] == "Success"        

    def hold(self):
        """cancels the bot’s current command queue then keeps the bot 
        stopped until countermanded by a higher priority command"""
        
        command = {
            'command':'execute_action',
            'action':'hold'
        }
        result = self.send_and_recv(command)

        print("Result of holding bot: ", result)
        return result["Status"] == "Success"

    def move(self, direction):
        """move the bot 1 grid cell in a given direction"""

        command = {
            'command':'execute_action',
            'action':'move',
            'params': {
                'direction':direction} # up, down, left, right
        }
        result = self.send_and_recv(command)

        print("Result of moving bot: ", result)
        return result["Status"] == "Success"
    
    def move_to(self, x: int, y: int):
        """moves the bot to a specified location on the floor"""
        #TODO: what if x, y not provided or out of range?

        command = {
            'command':'execute_action',
            'action':'move_to',
            'params': {
                'x':x,
                'y':y
            }
        }
        result = self.send_and_recv(command)

        print("Result of moving bot to a specific location: ", result)
        return result["Status"] == "Success"  

    def interact(self):
        """interacts with the station on the bot’s current tile"""
        #TODO: what are the possible options? need params?

        command = {
            'command':'execute_action',
            'action':'useStation'
        }
        result = self.send_and_recv(command)

        print("Result of interacting with the station: ", result)
        return result["Status"] == "Success"       

    def pickUp(self):
        """picks up an inventory box that is sitting on a cell"""

        command = {
            'command':'execute_action',
            'action':'pickUp'
        }
        result = self.send_and_recv(command)

        print("Result of picking up: ", result)
        return result["Status"] == "Success"  

    def putDown(self):
        """takes current inventory and sets it on the ground in a box on the current cell"""

        command = {
            'command':'execute_action',
            'action':'putDown'
        }
        result = self.send_and_recv(command)

        print("Result of putting down: ", result)
        return result["Status"] == "Success"  

    def harvest(self, target: int):
        """removes a plant from the soil tile and adds it to the bot’s inventory"""
        #TODO: if target not provided defaults to finding the first legal target in the list

        command = {
            'command':'execute_action',
            'action':'harvest',
            'params':{
                'target':target
            }
        }
        result = self.send_and_recv(command)

        print("Result of harvesting: ", result)
        return result["Status"] == "Success"  


    def pluck(self, target: int):
        """removes the fruit from a target plant and adds it to the bot’s inventory"""
        #TODO: if target not provided defaults to finding the first legal target in the list

        command = {
            'command':'execute_action',
            'action':'pluck',
            'params':{
                'target':target
            }
        }
        result = self.send_and_recv(command)

        print("Result of plucking: ", result)
        return result["Status"] == "Success"  

    def sample(self, target: int):
        """takes a nutrient solution sample from a plant that can then be turned in for analysis"""
        #TODO: if not provided it samples the tile instead?

        command = {
            'command':'execute_action',
            'action':'sample',
            'params':{
                'target':target
            }
        }
        result = self.send_and_recv(command)

        print("Result of sampling: ", result)
        return result["Status"] == "Success"  

    def spray(self, volume: int):
        """sprays an amount of nutrient solution from the bot’s reservoir onto the current tile"""
        #TODO: volume is int?

        command = {
            'command':'execute_action',
            'action':'spray',
            'params':{
                'volume':volume
            }
        }
        result = self.send_and_recv(command)

        print("Result of spraying: ", result)
        return result["Status"] == "Success"  

    def plant(self, target: int):
        """removes a target plant from the bot’s inventory and 
        adds it to the next available space in the current tile"""

        command = {
            'command':'execute_action',
            'action':'plant',
            'params':{
                'target':target
            }
        }
        result = self.send_and_recv(command)

        print("Result of planting: ", result)
        return result["Status"] == "Success"  

    def till(self):
        """Destroys all of the plants rooted in the current tile and 
        adds their collective nutrient solutions to the soil of the tile"""
        #TODO this looks like two tasks: 1) destroy plants, 2) add nutrient

        command = {
            'command': 'execute_action',
            'action': 'till'
        }
        result = self.send_and_recv(command)

        print("Result of tilling: ", result)
        return result["Status"] == "Success"  
