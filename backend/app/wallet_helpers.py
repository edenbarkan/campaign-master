from app import db
from app.models import Wallet, LedgerEntry


def get_or_create_wallet(user_id):
    """Get or create a wallet for a user."""
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance_micro=0, reserved_micro=0)
        db.session.add(wallet)
        db.session.commit()
    return wallet


def topup_balance(user_id, amount_micro, ref_type=None, ref_id=None):
    """
    Atomically top up user balance.
    Returns (success: bool, wallet: Wallet or None)
    """
    try:
        # Lock the wallet row for update
        wallet = Wallet.query.filter_by(user_id=user_id).with_for_update().first()
        
        if not wallet:
            wallet = Wallet(user_id=user_id, balance_micro=0, reserved_micro=0)
            db.session.add(wallet)
        
        # Update balance
        wallet.balance_micro += amount_micro
        
        # Create ledger entry
        ledger_entry = LedgerEntry(
            user_id=user_id,
            entry_type='topup',
            amount_micro=amount_micro,
            ref_type=ref_type,
            ref_id=ref_id
        )
        db.session.add(ledger_entry)
        
        db.session.commit()
        return True, wallet
    except Exception as e:
        db.session.rollback()
        return False, None


def spend_balance(user_id, amount_micro, ref_type=None, ref_id=None):
    """
    Atomically spend from available balance (balance_micro - reserved_micro).
    Returns (success: bool, wallet: Wallet or None)
    """
    try:
        # Lock the wallet row for update
        wallet = Wallet.query.filter_by(user_id=user_id).with_for_update().first()
        
        if not wallet:
            return False, None
        
        available = wallet.balance_micro - wallet.reserved_micro
        
        if available < amount_micro:
            db.session.rollback()
            return False, None
        
        # Update balance
        wallet.balance_micro -= amount_micro
        
        # Create ledger entry
        ledger_entry = LedgerEntry(
            user_id=user_id,
            entry_type='spend',
            amount_micro=amount_micro,
            ref_type=ref_type,
            ref_id=ref_id
        )
        db.session.add(ledger_entry)
        
        db.session.commit()
        return True, wallet
    except Exception as e:
        db.session.rollback()
        return False, None


def reserve_balance(user_id, amount_micro, ref_type=None, ref_id=None):
    """
    Atomically reserve balance (move from available to reserved).
    Returns (success: bool, wallet: Wallet or None)
    """
    try:
        # Lock the wallet row for update
        wallet = Wallet.query.filter_by(user_id=user_id).with_for_update().first()
        
        if not wallet:
            return False, None
        
        available = wallet.balance_micro - wallet.reserved_micro
        
        if available < amount_micro:
            db.session.rollback()
            return False, None
        
        # Update reserved balance
        wallet.reserved_micro += amount_micro
        
        # Create ledger entry
        ledger_entry = LedgerEntry(
            user_id=user_id,
            entry_type='reserve',
            amount_micro=amount_micro,
            ref_type=ref_type,
            ref_id=ref_id
        )
        db.session.add(ledger_entry)
        
        db.session.commit()
        return True, wallet
    except Exception as e:
        db.session.rollback()
        return False, None


def release_reserved(user_id, amount_micro, ref_type=None, ref_id=None):
    """
    Atomically release reserved balance (move from reserved back to available).
    Returns (success: bool, wallet: Wallet or None)
    """
    try:
        # Lock the wallet row for update
        wallet = Wallet.query.filter_by(user_id=user_id).with_for_update().first()
        
        if not wallet or wallet.reserved_micro < amount_micro:
            db.session.rollback()
            return False, None
        
        # Update reserved balance
        wallet.reserved_micro -= amount_micro
        
        # Create ledger entry
        ledger_entry = LedgerEntry(
            user_id=user_id,
            entry_type='release',
            amount_micro=amount_micro,
            ref_type=ref_type,
            ref_id=ref_id
        )
        db.session.add(ledger_entry)
        
        db.session.commit()
        return True, wallet
    except Exception as e:
        db.session.rollback()
        return False, None


def earn_balance(user_id, amount_micro, ref_type=None, ref_id=None):
    """
    Atomically add earned balance (for publishers).
    Returns (success: bool, wallet: Wallet or None)
    """
    try:
        # Lock the wallet row for update
        wallet = Wallet.query.filter_by(user_id=user_id).with_for_update().first()
        
        if not wallet:
            wallet = Wallet(user_id=user_id, balance_micro=0, reserved_micro=0)
            db.session.add(wallet)
        
        # Update balance
        wallet.balance_micro += amount_micro
        
        # Create ledger entry
        ledger_entry = LedgerEntry(
            user_id=user_id,
            entry_type='earn',
            amount_micro=amount_micro,
            ref_type=ref_type,
            ref_id=ref_id
        )
        db.session.add(ledger_entry)
        
        db.session.commit()
        return True, wallet
    except Exception as e:
        db.session.rollback()
        return False, None

