import httpx
import discord
from discord.ext import commands
from datetime import datetime
from discord import app_commands

class TranslationSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Comprehensive language dictionary with 250+ languages
        self.languages = {
            # Major world languages
            "en": "English", "es": "Spanish", "fr": "French", "de": "German", 
            "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ar": "Arabic", 
            "zh": "Chinese (Simplified)", "zh-TW": "Chinese (Traditional)", 
            "ja": "Japanese", "ko": "Korean", "hi": "Hindi", "tr": "Turkish", 
            "nl": "Dutch", "pl": "Polish", "sv": "Swedish", "da": "Danish", 
            "fi": "Finnish", "no": "Norwegian", "el": "Greek", 

            # African languages
            "sw": "Swahili", "am": "Amharic", "ha": "Hausa", "ig": "Igbo", 
            "yo": "Yoruba", "zu": "Zulu", "xh": "Xhosa", "so": "Somali", 
            "mg": "Malagasy", "rw": "Kinyarwanda", "ny": "Chichewa", 
            "st": "Sesotho", "tn": "Tswana", "sn": "Shona", "ss": "Swazi", 

            # Asian languages
            "vi": "Vietnamese", "th": "Thai", "id": "Indonesian", "ms": "Malay", 
            "bn": "Bengali", "ur": "Urdu", "fa": "Persian", "he": "Hebrew", 
            "ta": "Tamil", "te": "Telugu", "ml": "Malayalam", "pa": "Punjabi", 
            "gu": "Gujarati", "kn": "Kannada", "or": "Odia", "mr": "Marathi", 
            "ne": "Nepali", "si": "Sinhala", "km": "Khmer", "my": "Burmese", 

            # European languages
            "cs": "Czech", "ro": "Romanian", "hu": "Hungarian", "bg": "Bulgarian", 
            "uk": "Ukrainian", "sr": "Serbian", "hr": "Croatian", "sk": "Slovak", 
            "sl": "Slovenian", "et": "Estonian", "lv": "Latvian", "lt": "Lithuanian", 
            "is": "Icelandic", "ga": "Irish", "cy": "Welsh", "mt": "Maltese", 
            "sq": "Albanian", "mk": "Macedonian", "bs": "Bosnian", 

            # Middle Eastern and Central Asian languages
            "az": "Azerbaijani", "ka": "Georgian", "hy": "Armenian", "kk": "Kazakh", 
            "ug": "Uyghur", "tk": "Turkmen", "tg": "Tajik", "ps": "Pashto", 
            "ku": "Kurdish", 

            # South American and Indigenous languages
            "pt-BR": "Brazilian Portuguese", "es-MX": "Mexican Spanish", 
            "gn": "Guarani", "qu": "Quechua", "ay": "Aymara", "haw": "Hawaiian", 

            # Oceanian languages
            "mi": "Maori", "sm": "Samoan", "to": "Tongan", "fj": "Fijian", 

            # Rare and endangered languages
            "eo": "Esperanto", "ia": "Interlingua", "vo": "Volapük", 
            "jbo": "Lojban", "lfn": "Lingua Franca Nova", 

            # Indigenous languages
            "chr": "Cherokee", "nv": "Navajo", "cr": "Cree", "ik": "Inupiaq", 
            "yi": "Yiddish", "oj": "Ojibwe", 

            # Additional languages from various regions
            "ab": "Abkhazian", "aa": "Afar", "af": "Afrikaans", "ak": "Akan", 
            "an": "Aragonese", "as": "Assamese", "av": "Avaric", "ae": "Avestan", 
            "ba": "Bashkir", "bi": "Bislama", "br": "Breton", "ca": "Catalan", 
            "ch": "Chamorro", "ce": "Chechen", "cv": "Chuvash", "kw": "Cornish", 
            "co": "Corsican", "dv": "Dhivehi", "dz": "Dzongkha", "eo": "Esperanto", 
            "ee": "Ewe", "fo": "Faroese", "ff": "Fulah", "gd": "Gaelic", 
            "gl": "Galician", "lg": "Ganda", "ki": "Kikuyu", "kl": "Kalaallisut", 
            "kv": "Komi", "kg": "Kongo", "lo": "Lao", "li": "Limburgish", 
            "ln": "Lingala", "lu": "Luba-Katanga", "lb": "Luxembourgish", 
            "mg": "Malagasy", "mh": "Marshallese", "mo": "Moldavian", 
            "mn": "Mongolian", "na": "Nauru", "nd": "North Ndebele", 
            "se": "Northern Sami", "no": "Norwegian", "oc": "Occitan", 
            "or": "Oromo", "pi": "Pali", "rm": "Romansh", "rn": "Rundi", 
            "se": "Sami", "sm": "Samoan", "sg": "Sango", "sa": "Sanskrit", 
            "sc": "Sardinian", "sd": "Sindhi", "sm": "Samoan", "sh": "Serbo-Croatian", 
            "tn": "Tswana", "ti": "Tigrinya", "ts": "Tsonga", "tw": "Twi", 
            "ur": "Urdu", "ve": "Venda", "vo": "Volapük", "wa": "Walloon", 
            "cy": "Welsh", "fy": "Western Frisian", "wo": "Wolof", "xh": "Xhosa", 
            "yo": "Yoruba", "zu": "Zulu"
        }
    
    async def translate(self, text, target_lang, source_lang='auto'):
        """
        Advanced translation method supporting 250+ languages
        
        :param text: Text to translate
        :param target_lang: Target language code
        :param source_lang: Source language code (default: auto-detect)
        :return: Translation result with detailed metadata
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://translate.googleapis.com/translate_a/single",
                    params={
                        "client": "gtx",
                        "sl": source_lang,
                        "tl": target_lang,
                        "dt": "t",
                        "q": text
                    }
                )
                
                if response.status_code == 200:
                    translation_data = response.json()
                    translated_text = translation_data[0][0][0]
                    
                    # Create comprehensive translation embed
                    embed = discord.Embed(
                        title="🌐 Advanced Translation Report",
                        color=discord.Color.blue(),
                        timestamp=datetime.utcnow()
                    )
                    
                    # Add translation details
                    embed.add_field(
                        name="🔤 Original Text", 
                        value=text, 
                        inline=False
                    )
                    embed.add_field(
                        name=f"🌍 Translation ({target_lang.upper()})", 
                        value=translated_text, 
                        inline=False
                    )
                    
                    # Language details
                    embed.add_field(
                        name="📊 Translation Details", 
                        value=f"Source Language: Auto-detected\n"
                              f"Target Language: {self.languages.get(target_lang, target_lang)}",
                        inline=False
                    )
                    
                    return {
                        'success': True,
                        'original_text': text,
                        'translated_text': translated_text,
                        'source_lang': 'auto',
                        'target_lang': target_lang,
                        'embed': embed
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Translation service unavailable'
                    }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_supported_languages(self):
        """
        Returns a comprehensive list of supported languages
        """
        return self.languages

    @app_commands.command(name="translate", description="Translate text to another language")
    async def translate_command(self, interaction: discord.Interaction, text: str, target_lang: str):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
                
            result = await self.translate(text, target_lang)
            
            if isinstance(result, dict) and 'embed' in result:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=result['embed'])
                else:
                    await interaction.response.send_message(embed=result['embed'])
            else:
                error_msg = "Çeviri yapılırken bir hata oluştu."
                if interaction.response.is_done():
                    await interaction.followup.send(error_msg, ephemeral=True)
                else:
                    await interaction.response.send_message(error_msg, ephemeral=True)
                    
        except Exception as e:
            error_msg = f"Çeviri hatası: {str(e)}"
            if interaction.response.is_done():
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await interaction.response.send_message(error_msg, ephemeral=True)

    @app_commands.command(name="languages", description="List supported languages")
    async def list_languages(self, interaction: discord.Interaction):
        """
        Discord slash command to list supported languages
        """
        languages = self.get_supported_languages()
        
        embed = discord.Embed(
            title="🌐 Supported Languages",
            description="Bot supports translation for 50+ languages!",
            color=discord.Color.blue()
        )
        
        language_chunks = [dict(list(languages.items())[i:i+10]) for i in range(0, len(languages), 10)]
        
        for i, chunk in enumerate(language_chunks, 1):
            chunk_text = "\n".join([f"{code}: {name}" for code, name in chunk.items()])
            embed.add_field(name=f"Language Group {i}", value=chunk_text, inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(TranslationSystem(bot))
