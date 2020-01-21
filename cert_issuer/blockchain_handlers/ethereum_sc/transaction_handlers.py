import logging

from pycoin.serialize import b2h

from cert_issuer.blockchain_handlers.ethereum_sc.connectors import EthereumSCServiceProviderConnector
from cert_issuer.errors import InsufficientFundsError
from cert_issuer.blockchain_handlers.ethereum_sc import tx_utils
from cert_issuer.models import TransactionHandler
from cert_issuer.signer import FinalizableSigner


class EthereumSCTransactionHandler(TransactionHandler):
    def __init__(self, connector, tx_cost_constants, secret_manager, issuing_address, prepared_inputs=None):
        self.connector = connector
        self.tx_cost_constants = tx_cost_constants
        self.secret_manager = secret_manager
        self.issuing_address = issuing_address
        # input transactions are not needed for Ether
        self.prepared_inputs = prepared_inputs

    # inherited
    def ensure_balance(self):
        # testing etherscan api wrapper
        self.balance = self.connector.get_balance(self.issuing_address)

        # for now transaction cost will be a constant: (25000 gas estimate times 20Gwei gasprice) from tx_utils
        # can later be calculated inside EthereumTransaction_creator
        transaction_cost = self.tx_cost_constants.get_recommended_max_cost()
        logging.info('Total cost will be %d wei', transaction_cost)

        if transaction_cost > self.balance:
            error_message = 'Please add {} wei to the address {}'.format(
                transaction_cost - self.balance, self.issuing_address)
            logging.error(error_message)
            raise InsufficientFundsError(error_message)

    # starting point for issuing
    # inherited
    def issue_transaction(self, blockchain_bytes, app_config):
        eth_data_field = b2h(blockchain_bytes)

        # self.contract = ContractConnection(app_config)

        prepared_tx = self.connector.create_transaction("issue_hash", blockchain_bytes)
        signed_tx = self.sign_transaction(prepared_tx)

        # TODO
        # self.verify_transaction(signed_tx, eth_data_field)

        txid = self.broadcast_transaction(signed_tx)
        return txid

    def sign_transaction(self, prepared_tx):
        # stubbed from BitcoinTransactionHandler

        with FinalizableSigner(self.secret_manager) as signer:
            signed_tx = signer.sign_transaction(prepared_tx)

        logging.info('signed Ethereum trx = %s', signed_tx)
        return signed_tx

    def broadcast_transaction(self, signed_tx):
        txid = self.connector.broadcast_tx(signed_tx)
        return txid

    def verify_transaction(self, signed_tx, eth_data_field):
        tx_utils.verify_eth_transaction(signed_tx, eth_data_field)
