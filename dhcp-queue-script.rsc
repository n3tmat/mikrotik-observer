:local devName $"lease-hostname";
:if ([:len $devName] = 0) do={ :set devName "Unknown" };

:if ($leaseBound = "1") do={
    # We add 'max-limit=10M/10M' so the device actually has internet speed!
    /queue simple add name=($devName . "-" . $leaseActIP) target=$leaseActIP max-limit=10M/10M comment="Auto-Monitor"
} else={
    /queue simple remove [find comment="Auto-Monitor" and target=$leaseActIP]
}