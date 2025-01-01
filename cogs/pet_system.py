import discord
from discord import app_commands
from discord.ext import commands
import json
import random
import asyncio
from datetime import datetime

class Pet:
    def __init__(self, name, species):
        self.name = name
        self.species = species
        self.hunger = 100
        self.happiness = 100
        self.health = 100
        self.energy = 100
        self.level = 1
        self.exp = 0
        self.last_feed = datetime.now()
        self.last_play = datetime.now()

class PetSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pets = {}
        self.load_pets()
        self.pet_species = [
            # Canines
            "Wolf", "Fox", "Arctic Fox", "Husky", "German Shepherd", "Fennec Fox", "Coyote", "Dog", "husky",
            # Felines
            "Cat", "Lion", "Tiger", "Leopard", "Cheetah", "Lynx", "Caracal", "Serval", "Snow Leopard",
            # Dragons
            "Western Dragon", "Eastern Dragon", "Wyvern", "Drake", "Hydra", "Amphiptere",
            # Mythical Creatures
            "Unicorn", "Phoenix", "Gryphon", "Kitsune", "Dragon-Wolf", "Manticore", "Chimera",
            # Avians
            "Eagle", "Hawk", "Falcon", "Owl", "Raven", "Crow", "Peacock",
            # Prehistoric
            "Raptor", "T-Rex", "Pterodactyl", "Protogen", "Primagen",
            # Aquatic
            "Shark", "Dolphin", "Orca", "Sergal", "Manokit",
            # Hybrids
            "Wolf-Dragon", "Fox-Cat", "Lion-Dragon", "Tiger-Wolf",
            # Furry Favorites
            "Dutch Angel Dragon", "Wickerbeast", "Synth", "Avali", "Sergal", "Protogen",
            # More Exotic
            "Red Panda", "Raccoon", "Deer", "Elk", "Moose", "Bear", "Rabbit", "Jackalope",
            # Fantasy
            "Celestial Wolf", "Shadow Fox", "Crystal Dragon", "Spirit Wolf", "Neon Fox",
            # Additional Species
            "Maned Wolf", "Arctic Wolf", "Timber Wolf", "Grey Fox", "Silver Fox",
            "Snow Leopard", "Clouded Leopard", "Black Panther", "White Tiger", "Golden Lion",
            "Ice Dragon", "Fire Dragon", "Storm Dragon", "Crystal Dragon", "Cyber Dragon",
            "Demon Fox", "Angel Wolf", "Star Wolf", "Galaxy Dragon", "Void Fox",
            "Emerald Dragon", "Ruby Wolf", "Sapphire Fox", "Diamond Dog", "Pearl Cat",
            "Cosmic Dragon", "Lunar Wolf", "Solar Fox", "Nebula Cat", "Stellar Dog",
            "Tech Protogen", "Cyber Sergal", "Digital Dragon", "Binary Wolf", "Quantum Fox",
            "Ghost Wolf", "Spirit Fox", "Phantom Cat", "Wraith Dog", "Specter Dragon",
            "Rainbow Dragon", "Aurora Wolf", "Prism Fox", "Spectrum Dog", "Chromatic Cat"
        ]
        self.bot.loop.create_task(self.pet_status_update())

    def load_pets(self):
        try:
            with open('pets.json', 'r') as f:
                self.pets = json.load(f)
        except FileNotFoundError:
            self.pets = {}

    def save_pets(self):
        with open('pets.json', 'w') as f:
            json.dump(self.pets, f)

    @app_commands.command(name="pet", description="Show pet commands help")
    async def pet_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🐾 Pet System Commands",
            description="Available commands for your virtual pet!",
            color=discord.Color.blue()
        )
        embed.add_field(name="/pet-create", value="Create a new pet", inline=False)
        embed.add_field(name="/pet-status", value="Check your pet's status", inline=False)
        embed.add_field(name="/pet-feed", value="Feed your pet", inline=False)
        embed.add_field(name="/pet-play", value="Play with your pet", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pet-create", description="Create a new pet")
    @app_commands.describe(
        name="Your pet's name",
        species="Choose your pet's species"
    )
    async def pet_create(self, interaction: discord.Interaction, name: str, species: str):
        user_id = str(interaction.user.id)
        if user_id in self.pets:
            await interaction.response.send_message("You already have a pet!", ephemeral=True)
            return

        if species.title() not in self.pet_species:
            species_list = "\n".join(sorted(self.pet_species))
            await interaction.response.send_message(
                f"Invalid species! Please choose from:\n```\n{species_list}\n```",
                ephemeral=True
            )
            return

        pet = Pet(name, species)
        self.pets[user_id] = vars(pet)
        self.save_pets()
        
        embed = discord.Embed(
            title="🎉 New Pet Acquired!",
            description=f"Congratulations! You've adopted a {species} named {name}!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pet-status", description="Check your pet's status")
    async def pet_status(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.pets:
            await interaction.response.send_message("You don't have a pet yet!", ephemeral=True)
            return

        pet = self.pets[user_id]
        embed = discord.Embed(
            title=f"🐾 {pet['name']} - Level {pet['level']}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Species", value=pet['species'])
        embed.add_field(name="Hunger", value=f"{'🟩' * (pet['hunger']//10)}{'⬜' * (10-pet['hunger']//10)}")
        embed.add_field(name="Happiness", value=f"{'🟨' * (pet['happiness']//10)}{'⬜' * (10-pet['happiness']//10)}")
        embed.add_field(name="Health", value=f"{'❤️' * (pet['health']//10)}{'🖤' * (10-pet['health']//10)}")
        embed.add_field(name="Energy", value=f"{'⚡' * (pet['energy']//10)}{'⬜' * (10-pet['energy']//10)}")
        embed.add_field(name="Experience", value=f"{'🟦' * (pet['exp']//10)}{'⬜' * (10-pet['exp']//10)}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pet-feed", description="Feed your pet")
    async def pet_feed(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.pets:
            await interaction.response.send_message("You don't have a pet yet!", ephemeral=True)
            return

        pet = self.pets[user_id]
        if pet['hunger'] >= 90:
            await interaction.response.send_message(f"{pet['name']} is not hungry right now!", ephemeral=True)
            return

        pet['hunger'] = min(100, pet['hunger'] + 30)
        pet['health'] = min(100, pet['health'] + 5)
        self.save_pets()
        await interaction.response.send_message(f"🍖 {pet['name']} happily ate their food!")

    @app_commands.command(name="pet-play", description="Play with your pet")
    async def pet_play(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.pets:
            await interaction.response.send_message("You don't have a pet yet!", ephemeral=True)
            return

        pet = self.pets[user_id]
        if pet['energy'] < 20:
            await interaction.response.send_message(f"{pet['name']} is too tired to play!", ephemeral=True)
            return

        games = ["ball", "chase", "hide and seek", "fetch", "agility course"]
        game = random.choice(games)
        pet['happiness'] = min(100, pet['happiness'] + 20)
        pet['energy'] = max(0, pet['energy'] - 20)
        pet['exp'] += 10
        self.save_pets()
        await interaction.response.send_message(f"🎮 You played {game} with {pet['name']}!")

    async def pet_status_update(self):
        """Evcil hayvanların durumlarını periyodik olarak güncelle"""
        while True:
            for user_id, pet in self.pets.items():
                pet['hunger'] = max(0, pet['hunger'] - 2)
                pet['happiness'] = max(0, pet['happiness'] - 2)
                pet['energy'] = min(100, pet['energy'] + 5)
                
                if pet['hunger'] < 30:
                    pet['health'] = max(0, pet['health'] - 5)
                if pet['happiness'] < 30:
                    pet['health'] = max(0, pet['health'] - 3)

                if pet['exp'] >= 100:
                    pet['level'] += 1
                    pet['exp'] = 0
                
            self.save_pets()
            await asyncio.sleep(3600)  # Her saat başı güncelle

async def setup(bot):
    await bot.add_cog(PetSystem(bot))
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
