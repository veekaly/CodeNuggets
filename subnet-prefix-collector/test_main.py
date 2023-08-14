from ipaddress import IPv4Network, IPv4Address
import pytest
from unittest.mock import Mock
from main import list_prefixes, get_unreserved_range, get_subnet_cidr, get_prefixes_allocated_standalone_ips

@pytest.mark.parametrize("subnet_cidr_range, subnet_reservation_cidrs, expected_result", [
    ('100.64.0.0/18', [], [IPv4Network('100.64.0.0/18')]),
    ('100.64.0.0/18', [{"id": "src-xxx", "cidr": "100.64.0.0/19"},{"id": "src-xxx", "cidr": "100.64.32.0/20"}], [IPv4Network('100.64.48.0/20')]),
    ('100.64.128.0/18', [{"id": "src-xxx", "cidr": "100.64.144.0/20"},{"id": "src-xxx", "cidr": "100.64.160.0/19"}], [IPv4Network('100.64.128.0/20')]),
    ('100.64.0.0/18', [{"id": "src-xxx", "cidr": "100.64.16.0/21"},{"id": "src-xxx", "cidr": "100.64.44.0/22"}], [IPv4Network('100.64.0.0/20'), IPv4Network('100.64.24.0/21'), IPv4Network('100.64.48.0/20'), IPv4Network('100.64.32.0/21'), IPv4Network('100.64.40.0/22')]),
    ('100.64.0.0/18', [{"id": "src-xxx", "cidr": "100.64.8.0/22"},{"id": "src-xxx", "cidr": "100.64.32.0/21"},{"id": "src-xxx", "cidr": "100.64.48.0/22"}], [IPv4Network('100.64.40.0/21'), IPv4Network('100.64.56.0/21'), IPv4Network('100.64.52.0/22'), IPv4Network('100.64.16.0/20'), IPv4Network('100.64.0.0/21'), IPv4Network('100.64.12.0/22')])
])
def test_get_unreserved_range(subnet_cidr_range, subnet_reservation_cidrs, expected_result):
    assert get_unreserved_range(subnet_cidr_range, subnet_reservation_cidrs) == expected_result

@pytest.mark.parametrize("cidr_range, expected_result", [
    ('100.64.0.0/24', [IPv4Network('100.64.0.0/28'), IPv4Network('100.64.0.16/28'), IPv4Network('100.64.0.32/28'), IPv4Network('100.64.0.48/28'), IPv4Network('100.64.0.64/28'), IPv4Network('100.64.0.80/28'), IPv4Network('100.64.0.96/28'), IPv4Network('100.64.0.112/28'), IPv4Network('100.64.0.128/28'), IPv4Network('100.64.0.144/28'), IPv4Network('100.64.0.160/28'), IPv4Network('100.64.0.176/28'), IPv4Network('100.64.0.192/28'), IPv4Network('100.64.0.208/28'), IPv4Network('100.64.0.224/28'), IPv4Network('100.64.0.240/28')]),
])
def test_list_prefixes(cidr_range, expected_result):
    assert list_prefixes(cidr_range) == expected_result

@pytest.mark.parametrize("eni_ip_list, prefixes, expected_result", [
    ([IPv4Address('100.64.250.221')], [IPv4Network('100.64.255.224/28'), IPv4Network('100.64.255.240/28')], []),
    ([IPv4Address('100.64.250.221')], [IPv4Network('100.64.250.208/28'), IPv4Network('100.64.250.224/28')], [IPv4Network('100.64.250.208/28')]),
    ([], [], [])
])
def test_get_prefixes_allocated_standalone_ips(eni_ip_list, prefixes, expected_result):
    assert get_prefixes_allocated_standalone_ips(eni_ip_list, prefixes) == expected_result


if __name__ == "__main__":
    pytest.main()