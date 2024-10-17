from db_utils import update_player_field

class Player:
    def __init__(self, player_id=None, guild_id=None, data=None):
        self.player_id = player_id
        self.guild_id = guild_id
        if data:
            self.candy_in_bucket = data.get('candy_in_bucket', 0)
            self.successful_tricks = data.get('successful_tricks', 0)
            self.failed_tricks = data.get('failed_tricks', 0)
            self.treats_given = data.get('treats_given', 0)
            self.potions_purchased = data.get('potions_purchased', 0)
            self.active = data.get('active', False)
        else:
            self.candy_in_bucket = 0
            self.successful_tricks = 0
            self.failed_tricks = 0
            self.treats_given = 0
            self.potions_purchased = 0
            self.active = False

    def __repr__(self):
        return (f"Player(candy_in_bucket={self.candy_in_bucket}, "
                f"successful_tricks={self.successful_tricks}, "
                f"failed_tricks={self.failed_tricks}, "
                f"treats_given={self.treats_given}, "
                f"potions_purchased={self.potions_purchased}, "
                f"active={self.active})")

    def update_candy_in_bucket(self, amount):
        self.candy_in_bucket += amount

    def increment_successful_tricks(self):
        self.successful_tricks += 1

    def increment_failed_tricks(self):
        self.failed_tricks += 1

    def give_candy(self, amount):
        self.treats_given += amount

    def purchase_ticket(self):
        self.potions_purchased += 1

    def is_active(self):
        return self.active

    def save_to_db(self):#mm meh... i dont like this

        # Update the database with the revised fields
        update_player_field(self.player_id, self.guild_id, 'candy_in_bucket', self.candy_in_bucket)
        update_player_field(self.player_id, self.guild_id, 'successful_tricks', self.successful_tricks)
        update_player_field(self.player_id, self.guild_id, 'failed_tricks', self.failed_tricks)
        update_player_field(self.player_id, self.guild_id, 'treats_given', self.treats_given)
        update_player_field(self.player_id, self.guild_id, 'potions_purchased', self.potions_purchased)
        update_player_field(self.player_id, self.guild_id, 'active', self.active)

# Example usage:
# player = Player(candy_in_bucket=50, successful_tricks=5, failed_tricks=3, treats_given=10, potions_purchased=2, active=True)
# print(player)
