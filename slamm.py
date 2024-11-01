from dataclasses import dataclass

@dataclass
class Reserves:
    spot_reserves: float
    pass_reserves: float
    fail_reserves: float

class SLAMM:
    def __init__(self):
        self.base_reserves = Reserves(0, 0, 0)
        self.quote_reserves = Reserves(0, 0, 0)

    def print_prices(self):
        print("spot price", self.quote_reserves.spot_reserves / self.base_reserves.spot_reserves)
        print("pass price", (self.quote_reserves.pass_reserves + self.quote_reserves.spot_reserves) / (self.base_reserves.pass_reserves + self.base_reserves.spot_reserves))
        print("fail price", (self.quote_reserves.fail_reserves + self.quote_reserves.spot_reserves) / (self.base_reserves.fail_reserves + self.base_reserves.spot_reserves))

    def split(self, base_or_quote, amount):
        reserves = getattr(self, f"{base_or_quote}_reserves")

        reserves.spot_reserves -= amount
        reserves.pass_reserves += amount 
        reserves.fail_reserves += amount 


    def add_reserves(self, base_amount, quote_amount):
        self.base_reserves.spot_reserves += base_amount
        self.quote_reserves.spot_reserves += quote_amount

    def compute_reserves(self, market_type):
        base_reserves = self.base_reserves.spot_reserves
        quote_reserves = self.quote_reserves.spot_reserves

        if market_type == "pass":
            base_reserves += self.base_reserves.pass_reserves
            quote_reserves += self.quote_reserves.pass_reserves
        elif market_type == "fail":
            base_reserves += self.base_reserves.fail_reserves
            quote_reserves += self.quote_reserves.fail_reserves

        return base_reserves, quote_reserves

    def swap(self, amount_in, is_buy, market_type):
        amount_out = 0

        if market_type == "spot":
            invariant = self.base_reserves.spot_reserves * self.quote_reserves.spot_reserves

            if is_buy:
                pre_base_reserves = self.base_reserves.spot_reserves

                self.quote_reserves.spot_reserves += amount_in
                self.base_reserves.spot_reserves = invariant / self.quote_reserves.spot_reserves
                amount_out = pre_base_reserves - self.base_reserves.spot_reserves
            else:
                pre_quote_reserves = self.quote_reserves.spot_reserves

                self.base_reserves.spot_reserves += amount_in
                self.quote_reserves.spot_reserves = invariant / self.base_reserves.spot_reserves
                amount_out = pre_quote_reserves - self.quote_reserves.spot_reserves
        elif market_type == "pass":
            invariant = (self.base_reserves.spot_reserves + self.base_reserves.pass_reserves) * (self.quote_reserves.spot_reserves + self.quote_reserves.pass_reserves)

            if is_buy:
                self.quote_reserves.pass_reserves += amount_in

                new_base_reserves = invariant / (self.quote_reserves.spot_reserves + self.quote_reserves.pass_reserves)
                
                amount_out = (self.base_reserves.spot_reserves + self.base_reserves.pass_reserves) - new_base_reserves

                # split to create sufficient `amount_out`

                if amount_out > self.base_reserves.pass_reserves:
                    base_to_split = amount_out - self.base_reserves.pass_reserves

                    # need to also split an equal share of quote reserves to keep
                    # the ratio of quote reserves to base reserves the same
                    share_of_base_reserves = base_to_split / self.base_reserves.spot_reserves
                    quote_to_split = share_of_base_reserves * self.quote_reserves.spot_reserves

                    self.split("base", base_to_split)
                    self.split("quote", quote_to_split)

                self.base_reserves.pass_reserves -= amount_out
            else:
                invariant = (self.base_reserves.spot_reserves + self.base_reserves.pass_reserves) * (self.quote_reserves.spot_reserves + self.quote_reserves.pass_reserves)
                
                self.base_reserves.pass_reserves += amount_in

                new_quote_reserves = invariant / (self.base_reserves.spot_reserves + self.base_reserves.pass_reserves)
                
                amount_out = (self.quote_reserves.spot_reserves + self.quote_reserves.pass_reserves) - new_quote_reserves

                # split to create sufficient `amount_out`
                if amount_out > self.quote_reserves.pass_reserves:
                    quote_to_split = amount_out - self.quote_reserves.pass_reserves

                    # need to also split an equal share of base reserves to keep
                    # the ratio of quote reserves to base reserves the same
                    share_of_quote_reserves = quote_to_split / self.quote_reserves.spot_reserves
                    base_to_split = share_of_quote_reserves * self.base_reserves.spot_reserves

                    self.quote_reserves.spot_reserves -= quote_to_split
                    self.quote_reserves.pass_reserves += quote_to_split
                    self.quote_reserves.fail_reserves += quote_to_split

                    self.base_reserves.spot_reserves -= base_to_split
                    self.base_reserves.pass_reserves += base_to_split
                    self.base_reserves.fail_reserves += base_to_split

                self.quote_reserves.pass_reserves -= amount_out

                
        # there's mergeable tokens 
        quote_mergeable = min(self.quote_reserves.pass_reserves, self.quote_reserves.fail_reserves)
        base_mergeable = min(self.base_reserves.pass_reserves, self.base_reserves.fail_reserves)

        if quote_mergeable > 0 and base_mergeable > 0:
            #  merge equal proportions
            quote_mergeable_proportion = quote_mergeable / self.quote_reserves.spot_reserves
            base_mergeable_proportion = base_mergeable / self.base_reserves.spot_reserves

            merge_proportion = min(quote_mergeable_proportion, base_mergeable_proportion)
            
            quote_to_merge = merge_proportion * self.quote_reserves.spot_reserves
            base_to_merge = merge_proportion * self.base_reserves.spot_reserves

            self.quote_reserves.spot_reserves += quote_to_merge
            self.quote_reserves.pass_reserves -= quote_to_merge
            self.quote_reserves.fail_reserves -= quote_to_merge

            self.base_reserves.spot_reserves += base_to_merge
            self.base_reserves.pass_reserves -= base_to_merge
            self.base_reserves.fail_reserves += base_to_merge

        return amount_out

    # def get_expected_out(self, is_buying, amount, market_type):
    #     base_reserves = self.base_reserves.spot_reserves
    #     quote_reserves = self.quote_reserves.spot_reserves

    #     if market_type == "pass":
    #         base_reserves += self.base_reserves.pass_reserves
    #         quote_reserves += self.quote_reserves.pass_reserves
    #     elif market_type == "fail":
    #         base_reserves += self.base_reserves.fail_reserves
    #         quote_reserves += self.quote_reserves.fail_reserves

    #     invariant = base_reserves * quote_reserves

    #     if is_buying:
    #         new_quote_reserves = quote_reserves + amount
    #         new_base_reserves = invariant / new_quote_reserves
    #         return base_reserves - new_base_reserves
    #     else:
    #         new_base_reserves = base_reserves + amount
    #         new_quote_reserves = invariant / new_base_reserves
    #         return quote_reserves - new_quote_reserves

def main():
    slamm = SLAMM()
    slamm.add_reserves(100, 100)
    # print(slamm.swap(1, True, "spot"))
    # print(slamm.quote_reserves)
    # print(slamm.base_reserves)
    # slamm.print_prices()

    # print(slamm.swap(1, True, "pass"))
    # print(slamm.quote_reserves)
    # print(slamm.base_reserves)
    # slamm.print_prices()

    # print(slamm.swap(1, True, "pass"))
    # print(slamm.quote_reserves)
    # print(slamm.base_reserves)
    # slamm.print_prices()

    # print(slamm.swap(1, False, "spot"))
    # print(slamm.quote_reserves)
    # print(slamm.base_reserves)
    # slamm.print_prices()

    print(slamm.swap(1, True, "pass"))
    print(slamm.quote_reserves)
    print(slamm.base_reserves)
    slamm.print_prices()

if __name__ == "__main__":
    main()