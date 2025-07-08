## Issues during game play

- [x] TypeError: 'int' object is not subscriptable
    - was due to wrong data type pass in function:
        - I was trying to send target_id in in the slot of target_data (target_id["candy_in_bucket"] )
        - update_player_field(target_id, guild_id, 'candy_in_bucket', target_data["candy_in_bucket"] + given_candy)
- [x] /game add player': Error Command 'player' raised an exception: IntegrityError: UNIQUE constraint failed: players.player_id, players.guild_id
    - this happens when someone addes wickedWhiskers to the game and then tries to add them again
    - due to player already being present in the game and not validating. Updated the sql util to respond false (did not add player exists) for better handling
- [x] unable to treat candy:
    - noticed when i was low on candy and tried to give all (9 pieces), then also occured on 8 pieces
    - Error: Command 'treat' raised an exception: TypeError: '<' not supported between instances of 'builtin_function_or_method' and 'float'
    - random function wasn't set properly, had `random.random < .05:` should have ben `random.random() < .05:` 
- [] i couldn't modify the admin channel with /bot set channel (which it should honestly), update command worked - make this more apparent.
- [] add admin channel responses for updates to cauldron or player or when cast event is performed.

## Observations

- tricking is the prefered command
- make luna give events a higher probability
    - this probably wasn't being seen because of the random imrporper above `'builtin_function_or_method' and 'float'`

## Suggestions

- allow players to interact with the characters
- allow type of trick
    - ie, ding dong ditch, toilet paper toss, ect
- Explain who wickedWhiskers is (and other players)

