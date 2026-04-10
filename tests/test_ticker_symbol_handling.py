import unittest

from cli.utils import normalize_ticker_symbol, FuturesTicker
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    build_instrument_context_from_ticker,
)


class TestNormalizeTickerSymbol(unittest.TestCase):
    def test_species_only(self):
        result = normalize_ticker_symbol("rb")
        self.assertEqual(result.species, "RB")
        self.assertIsNone(result.exchange)
        self.assertEqual(result.position, "Long")

    def test_species_only_upper(self):
        result = normalize_ticker_symbol("RB")
        self.assertEqual(result.species, "RB")
        self.assertEqual(result.position, "Long")

    def test_with_exchange(self):
        result = normalize_ticker_symbol("SHFE:rb")
        self.assertEqual(result.species, "RB")
        self.assertEqual(result.exchange, "SHFE")
        self.assertEqual(result.position, "Long")

    def test_with_position_long(self):
        result = normalize_ticker_symbol("rb|Long")
        self.assertEqual(result.species, "RB")
        self.assertIsNone(result.exchange)
        self.assertEqual(result.position, "Long")

    def test_with_position_short(self):
        result = normalize_ticker_symbol("rb|Short")
        self.assertEqual(result.species, "RB")
        self.assertIsNone(result.exchange)
        self.assertEqual(result.position, "Short")

    def test_full_format(self):
        result = normalize_ticker_symbol("SHFE:rb|Short")
        self.assertEqual(result.species, "RB")
        self.assertEqual(result.exchange, "SHFE")
        self.assertEqual(result.position, "Short")

    def test_full_format_lowercase(self):
        result = normalize_ticker_symbol("shfe:rb|short")
        self.assertEqual(result.species, "RB")
        self.assertEqual(result.exchange, "SHFE")
        self.assertEqual(result.position, "Short")

    def test_if_with_position(self):
        result = normalize_ticker_symbol("IF|Long")
        self.assertEqual(result.species, "IF")
        self.assertEqual(result.position, "Long")

    def test_ceshi_futures(self):
        result = normalize_ticker_symbol("DCE:m")
        self.assertEqual(result.species, "M")
        self.assertEqual(result.exchange, "DCE")
        self.assertEqual(result.position, "Long")

    def test_czce_futures(self):
        result = normalize_ticker_symbol("CZCE:SF|Short")
        self.assertEqual(result.species, "SF")
        self.assertEqual(result.exchange, "CZCE")
        self.assertEqual(result.position, "Short")

    def test_cffex_futures(self):
        result = normalize_ticker_symbol("CFFEX:IF")
        self.assertEqual(result.species, "IF")
        self.assertEqual(result.exchange, "CFFEX")
        self.assertEqual(result.position, "Long")

    def test_legacy_stock_format_preserved(self):
        result = normalize_ticker_symbol("AAPL")
        self.assertEqual(result.species, "AAPL")
        self.assertIsNone(result.exchange)
        self.assertEqual(result.position, "Long")

    def test_legacy_toronto_format(self):
        result = normalize_ticker_symbol("cnc.to")
        self.assertEqual(result.species, "CNC.TO")
        self.assertEqual(result.position, "Long")


class TestFuturesTickerDisplay(unittest.TestCase):
    def test_str_representation(self):
        ticker = FuturesTicker(species="rb", exchange="SHFE", position="Long", raw_input="SHFE:rb")
        self.assertEqual(str(ticker), "SHFE:RB|Long")

    def test_str_without_exchange(self):
        ticker = FuturesTicker(species="IF", exchange=None, position="Short", raw_input="IF|Short")
        self.assertEqual(str(ticker), "IF|Short")

    def test_display_name(self):
        ticker = FuturesTicker(species="rb", exchange=None, position="Long", raw_input="rb")
        self.assertEqual(ticker.display_name, "螺纹钢")

    def test_display_name_if(self):
        ticker = FuturesTicker(species="IF", exchange=None, position="Long", raw_input="IF")
        self.assertEqual(ticker.display_name, "沪深300股指")


class TestBuildInstrumentContext(unittest.TestCase):
    def test_basic_species_context(self):
        context = build_instrument_context("rb")
        self.assertIn("RB", context)
        self.assertIn("螺纹钢", context)
        self.assertIn("Long", context)
        self.assertIn("main contract codes", context)

    def test_with_exchange_context(self):
        context = build_instrument_context("rb", exchange="SHFE")
        self.assertIn("SHFE:RB", context)
        self.assertIn("SHFE", context)
        self.assertIn("Shanghai", context)

    def test_long_position_context(self):
        context = build_instrument_context("IF", position="Long")
        self.assertIn("LONG", context)
        self.assertIn("price to rise", context)

    def test_short_position_context(self):
        context = build_instrument_context("IF", position="Short")
        self.assertIn("SHORT", context)
        self.assertIn("price to fall", context)


class TestBuildInstrumentContextFromTicker(unittest.TestCase):
    def test_species_only(self):
        context = build_instrument_context_from_ticker("rb")
        self.assertIn("RB", context)
        self.assertIn("Long", context)

    def test_with_exchange(self):
        context = build_instrument_context_from_ticker("SHFE:rb")
        self.assertIn("SHFE:RB", context)

    def test_with_position_long(self):
        context = build_instrument_context_from_ticker("rb|Long")
        self.assertIn("LONG", context)
        self.assertIn("price to rise", context)

    def test_with_position_short(self):
        context = build_instrument_context_from_ticker("IF|Short")
        self.assertIn("SHORT", context)
        self.assertIn("price to fall", context)

    def test_full_format(self):
        context = build_instrument_context_from_ticker("DCE:m|Short")
        self.assertIn("DCE:M", context)
        self.assertIn("Short", context)


class TestPositionDirectionSupport(unittest.TestCase):
    """Test that position direction (Long/Short) is properly supported throughout the system."""

    def test_all_exchanges_with_long_position(self):
        """Test all four Chinese futures exchanges with Long position."""
        exchanges = ["SHFE", "DCE", "CZCE", "CFFEX"]
        for exchange in exchanges:
            ticker_str = f"{exchange}:rb|Long"
            ticker = normalize_ticker_symbol(ticker_str)
            self.assertEqual(ticker.exchange, exchange)
            self.assertEqual(ticker.position, "Long")
            self.assertEqual(ticker.species, "RB")

    def test_all_exchanges_with_short_position(self):
        """Test all four Chinese futures exchanges with Short position."""
        exchanges = ["SHFE", "DCE", "CZCE", "CFFEX"]
        for exchange in exchanges:
            ticker_str = f"{exchange}:rb|Short"
            ticker = normalize_ticker_symbol(ticker_str)
            self.assertEqual(ticker.exchange, exchange)
            self.assertEqual(ticker.position, "Short")
            self.assertEqual(ticker.species, "RB")

    def test_build_instrument_context_with_long_position(self):
        """Test build_instrument_context correctly describes Long position."""
        context = build_instrument_context("rb", exchange="SHFE", position="Long")
        self.assertIn("LONG", context)
        self.assertIn("price to rise", context)
        self.assertNotIn("price to fall", context)

    def test_build_instrument_context_with_short_position(self):
        """Test build_instrument_context correctly describes Short position."""
        context = build_instrument_context("IF", position="Short")
        self.assertIn("SHORT", context)
        self.assertIn("price to fall", context)
        self.assertNotIn("price to rise", context)

    def test_futures_ticker_str_long(self):
        """Test FuturesTicker string representation for Long position."""
        ticker = FuturesTicker(species="rb", exchange="DCE", position="Long", raw_input="DCE:rb|Long")
        self.assertEqual(str(ticker), "DCE:RB|Long")

    def test_futures_ticker_str_short(self):
        """Test FuturesTicker string representation for Short position."""
        ticker = FuturesTicker(species="IF", exchange="CFFEX", position="Short", raw_input="CFFEX:IF|Short")
        self.assertEqual(str(ticker), "CFFEX:IF|Short")


class TestPropagatorPositionDirection(unittest.TestCase):
    """Test that position_direction is properly initialized in propagator."""

    def test_create_initial_state_with_long(self):
        from tradingagents.graph.propagation import Propagator
        propagator = Propagator()
        state = propagator.create_initial_state("rb", "2024-05-10", "Long")
        self.assertEqual(state["position_direction"], "Long")
        self.assertEqual(state["company_of_interest"], "rb")

    def test_create_initial_state_with_short(self):
        from tradingagents.graph.propagation import Propagator
        propagator = Propagator()
        state = propagator.create_initial_state("IF|Short", "2024-05-10", "Short")
        self.assertEqual(state["position_direction"], "Short")
        self.assertEqual(state["company_of_interest"], "IF|Short")

    def test_create_initial_state_default_long(self):
        from tradingagents.graph.propagation import Propagator
        propagator = Propagator()
        state = propagator.create_initial_state("rb", "2024-05-10")
        self.assertEqual(state["position_direction"], "Long")


class TestChineseFuturesSpecies(unittest.TestCase):
    """Test all major Chinese futures species are properly recognized."""

    def test_metals(self):
        """Test precious and base metals."""
        metals = ["au", "ag", "cu", "al", "zn", "pb", "ni", "sn", "ss"]
        for metal in metals:
            ticker = normalize_ticker_symbol(metal)
            self.assertEqual(ticker.species, metal.upper())
            self.assertEqual(ticker.position, "Long")

    def test_black_belts(self):
        """Test black commodity futures (steel, iron, coking coal)."""
        black_belts = ["rb", "hc", "i", "j", "jm"]
        for species in black_belts:
            ticker = normalize_ticker_symbol(species)
            self.assertEqual(ticker.species, species.upper())

    def test_agricultural(self):
        """Test agricultural futures."""
        agricultural = ["m", "y", "p", "a", "b", "c", "cs"]
        for species in agricultural:
            ticker = normalize_ticker_symbol(species)
            self.assertEqual(ticker.species, species.upper())

    def test_financial_futures(self):
        """Test financial futures (index futures)."""
        financial = ["IF", "IH", "IC", "IM"]
        for species in financial:
            ticker = normalize_ticker_symbol(species)
            self.assertEqual(ticker.species, species.upper())
            # Display name should work for all financial futures
            ticker_obj = FuturesTicker(species=species, exchange=None, position="Long", raw_input=species)
            self.assertIsNotNone(ticker_obj.display_name)


if __name__ == "__main__":
    unittest.main()
