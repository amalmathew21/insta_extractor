# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class MyscraperPipeline:
    def process_item(self, item, spider):
        return item

import json

class SplitByTypePipeline:
    def open_spider(self, spider):
        self.files = {
            "Post":    open("posts.json", "w"),
            "PostComment": open("post_comments.json", "w"),
            "Profile": open("profiles.json", "w"),
            "Reels": open("reels.json", "w"),
            "ReelComment": open("reels_comments.json", "w"),
            "Inputs": open("inputs.json", "w"),
        }
        self.first = {k: True for k in self.files}

        for f in self.files.values():
            f.write("[\n")

    def close_spider(self, spider):
        for f in self.files.values():
            f.write("\n]")
            f.close()

    def process_item(self, item, spider):
        item_type = type(item).__name__
        f = self.files.get(item_type)
        if f:
            if not self.first[item_type]:
                f.write(",\n")
            f.write(json.dumps(dict(item), ensure_ascii=False))
            self.first[item_type] = False
        return item