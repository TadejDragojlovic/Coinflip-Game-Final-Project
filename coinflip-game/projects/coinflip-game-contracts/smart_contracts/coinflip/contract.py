import beaker
import pyteal as pt

"""
Author: Tadej Dragojlovic
Created: 31/03/2024
"""

class CoinflipState:
    player_a_choice = beaker.GlobalStateValue(
        stack_type = pt.TealType.bytes,
        descr = "First player's side of the coin",
        default = pt.Bytes("Not chosen yet"),
    )

    player_b_choice = beaker.GlobalStateValue(
        stack_type = pt.TealType.bytes,
        descr = "Second player's side of the coin",
        default = pt.Bytes("Not chosen yet"),
    )

    player_a_account = beaker.GlobalStateValue(
        stack_type = pt.TealType.bytes,
        descr = "First player's account",
        default = pt.Bytes("Empty"),
    )

    player_b_account = beaker.GlobalStateValue(
        stack_type = pt.TealType.bytes,
        descr = "Second player's account",
        default = pt.Bytes("Empty"),
    )

    wager = beaker.GlobalStateValue(
        stack_type = pt.TealType.uint64,
        descr = "Betting amount for the coinflip",
        default = pt.Int(0),
    )

    player_games_won = beaker.LocalStateValue(
        stack_type = pt.TealType.uint64,
        descr = "Amount of coinflip games won",
        default = pt.Int(0),
    )

app = beaker.Application("coinflip", state=CoinflipState)

@app.external
def hello(name: pt.abi.String, *, output: pt.abi.String) -> pt.Expr:
    return output.set(pt.Concat(pt.Bytes("Hello, "), name.get()))

@app.create(bare=True)
def create() -> pt.Expr:
    """ Method for creating the smart contract, intializing global state """

    return app.initialize_global_state()

@app.opt_in(bare=True)
def opt_in() -> pt.Expr:
    """ Optin method """

    return pt.Seq(
        # TODO: check using conditional statements whether we need to fill player a slot, player b, or if it's full

        app.initialize_local_state(addr=pt.Txn.sender())
    )

@app.external(authorize=beaker.Authorize.opted_in())
def start_game(payment: pt.abi.PaymentTransaction, choice: pt.abi.String, *, output: pt.abi.String) -> pt.Expr:
    """
    Player A initiates the game, he pays the wager he wants for the game and then chooses the side of the coin ("Heads" or "Tails")
    """

    return pt.Seq(
        pt.Assert(
            pt.And(
                payment.type_spec().txn_type_enum() == pt.TxnType.Payment, # Making sure it's the correct TRANSACTION TYPE
                app.state.wager.get() == pt.Int(0),
                payment.get().receiver() == pt.Global.current_application_address(), # Making sure the user put the correct application address
                app.state.player_a_account.get() == pt.Bytes("Empty"),
                app.state.player_a_choice.get() == pt.Bytes("Not chosen yet"),
            )

            # TODO: Need to add checks whether user inputed the side correctly (heads/tails in any form should be allowed)
        ),

        app.state.player_a_account.set(pt.Txn.sender()),

        # TODO: if the user inputed the correct word (tails/heads) but in improper form (HEAds, HEADS, hEaDS, etc.), transform into correct using subroutine
        app.state.player_a_choice.set(choice.get()),

        app.state.wager.set(payment.get().amount()),

        output.set(pt.Bytes("Successfull.")),
    )

@app.external(authorize = beaker.Authorize.opted_in())
def join_game(payment: pt.abi.PaymentTransaction, *, output: pt.abi.String) -> pt.Expr:
    """
    Player B joins the game, gets the side that's left (player A picks first), pays the wager and waits for the game to resolve by player A
    """

    return pt.Seq(
        pt.Assert(
            pt.And(
                payment.type_spec().txn_type_enum() == pt.TxnType.Payment,

                # Making sure that the slot B isn't filled and that slot A is
                app.state.player_a_account.get() != pt.Bytes("Empty"), 
                app.state.player_b_account.get() == pt.Bytes("Empty"),

                payment.get().receiver() == pt.Global.current_application_address(),
                app.state.wager.get() == payment.get().amount(),
            )
        ),

        app.state.player_b_account.set(pt.Txn.sender()),
        app.state.player_b_choice.set(leftover_side(app.state.player_a_choice.get())),

        output.set(pt.Bytes("200.")),
    )

@pt.Subroutine(pt.TealType.bytes)
def leftover_side(player_a_choice: pt.Expr) -> pt.Expr:
    """
    Simple helper function that returns the leftover side of the coin
    """

    return pt.Seq(
        pt.If(player_a_choice == pt.Bytes("Heads"))
        .Then(pt.Bytes("Tails"))
        .Else(pt.Bytes("Heads"))
    )