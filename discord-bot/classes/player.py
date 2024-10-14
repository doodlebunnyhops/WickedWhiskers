from db_utils import update_player_field

class Player:
    def __init__(self, player_id=None, guild_id=None, data=None):
        self.player_id = player_id
        self.guild_id = guild_id
        if data:
            self.candy_count = data.get('candy_count', 0)
            self.successful_steals = data.get('successful_steals', 0)
            self.failed_steals = data.get('failed_steals', 0)
            self.candy_given = data.get('candy_given', 0)
            self.tickets_purchased = data.get('tickets_purchased', 0)
            self.active = data.get('active', False)
        else:
            self.candy_count = 0
            self.successful_steals = 0
            self.failed_steals = 0
            self.candy_given = 0
            self.tickets_purchased = 0
            self.active = False

    def __repr__(self):
        return (f"Player(candy_count={self.candy_count}, "
                f"successful_steals={self.successful_steals}, "
                f"failed_steals={self.failed_steals}, "
                f"candy_given={self.candy_given}, "
                f"tickets_purchased={self.tickets_purchased}, "
                f"active={self.active})")

    def update_candy_count(self, amount):
        self.candy_count += amount

    def increment_successful_steals(self):
        self.successful_steals += 1

    def increment_failed_steals(self):
        self.failed_steals += 1

    def give_candy(self, amount):
        self.candy_given += amount

    def purchase_ticket(self):
        self.tickets_purchased += 1

    def is_active(self):
        return self.active

    def save_to_db(self):#mm meh... i dont like this

        # Update the database with the revised fields
        update_player_field(self.player_id, self.guild_id, 'candy_count', self.candy_count)
        update_player_field(self.player_id, self.guild_id, 'successful_steals', self.successful_steals)
        update_player_field(self.player_id, self.guild_id, 'failed_steals', self.failed_steals)
        update_player_field(self.player_id, self.guild_id, 'candy_given', self.candy_given)
        update_player_field(self.player_id, self.guild_id, 'tickets_purchased', self.tickets_purchased)
        update_player_field(self.player_id, self.guild_id, 'active', self.active)

# Example usage:
# player = Player(candy_count=50, successful_steals=5, failed_steals=3, candy_given=10, tickets_purchased=2, active=True)
# print(player)
